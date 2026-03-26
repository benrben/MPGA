"""Tests for mpga.evidence.ast -- converted from ast.test.ts."""

from pathlib import Path

import pytest

from mpga.core.scanner import detect_language
from mpga.evidence.ast import extract_symbols, find_symbol, verify_range


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    def test_maps_ts_to_typescript(self):
        assert detect_language("src/index.ts") == "typescript"

    def test_maps_tsx_to_typescript(self):
        assert detect_language("App.tsx") == "typescript"

    def test_maps_js_to_javascript(self):
        assert detect_language("lib/utils.js") == "javascript"

    def test_maps_jsx_to_javascript(self):
        assert detect_language("components/App.jsx") == "javascript"

    def test_maps_mjs_to_javascript(self):
        assert detect_language("module.mjs") == "javascript"

    def test_maps_py_to_python(self):
        assert detect_language("main.py") == "python"

    def test_maps_go_to_go(self):
        assert detect_language("cmd/server.go") == "go"

    def test_maps_rs_to_rust(self):
        assert detect_language("src/lib.rs") == "rust"

    def test_maps_java_to_java(self):
        assert detect_language("src/Main.java") == "java"

    def test_maps_cs_to_csharp(self):
        assert detect_language("Program.cs") == "csharp"

    def test_maps_rb_to_ruby(self):
        assert detect_language("app.rb") == "ruby"

    def test_maps_php_to_php(self):
        assert detect_language("index.php") == "php"

    def test_returns_unknown_for_unrecognized_extension(self):
        assert detect_language("file.unknown") == "other"

    def test_returns_unknown_for_files_with_no_extension(self):
        assert detect_language("Makefile") == "other"


# ---------------------------------------------------------------------------
# extract_symbols
# ---------------------------------------------------------------------------


class TestExtractSymbols:
    def test_returns_empty_list_for_nonexistent_file(self, tmp_path: Path):
        result = extract_symbols("nonexistent.ts", str(tmp_path))
        assert result == []

    def test_extracts_typescript_function_declarations(self, tmp_path: Path):
        (tmp_path / "funcs.ts").write_text(
            "export function greet(name: string): string {\n"
            "  return `Hello ${name}`;\n"
            "}\n"
            "\n"
            "function helper() {\n"
            "  return 42;\n"
            "}\n"
        )
        symbols = extract_symbols("funcs.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "greet" in names
        assert "helper" in names
        assert next(s for s in symbols if s.name == "greet").type == "function"
        assert next(s for s in symbols if s.name == "helper").type == "function"

    def test_extracts_async_function_declarations(self, tmp_path: Path):
        (tmp_path / "async.ts").write_text(
            'export async function fetchData() {\n'
            '  return await fetch("/api");\n'
            '}\n'
        )
        symbols = extract_symbols("async.ts", str(tmp_path))
        assert len(symbols) == 1
        assert symbols[0].name == "fetchData"
        assert symbols[0].type == "function"

    def test_extracts_typescript_class_declarations(self, tmp_path: Path):
        (tmp_path / "classes.ts").write_text(
            "export class UserService {\n"
            "  getUser() {\n"
            "    return null;\n"
            "  }\n"
            "}\n"
            "\n"
            "abstract class BaseModel {\n"
            "  abstract validate(): boolean;\n"
            "}\n"
        )
        symbols = extract_symbols("classes.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "UserService" in names
        assert "BaseModel" in names
        assert next(s for s in symbols if s.name == "UserService").type == "class"
        assert next(s for s in symbols if s.name == "BaseModel").type == "class"

    def test_extracts_typescript_type_and_interface_declarations(self, tmp_path: Path):
        (tmp_path / "types.ts").write_text(
            "export type UserId = string;\n"
            "\n"
            "export interface Config {\n"
            "  host: string;\n"
            "  port: number;\n"
            "}\n"
            "\n"
            "type Internal = { key: string };\n"
        )
        symbols = extract_symbols("types.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "UserId" in names
        assert "Config" in names
        assert "Internal" in names
        for s in symbols:
            if s.name in ("UserId", "Config", "Internal"):
                assert s.type == "type"

    def test_extracts_arrow_function_assignments(self, tmp_path: Path):
        (tmp_path / "arrows.ts").write_text(
            "export const add = (a: number, b: number) => a + b;\n"
            "\n"
            "const multiply = (x: number, y: number) => {\n"
            "  return x * y;\n"
            "};\n"
        )
        symbols = extract_symbols("arrows.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "add" in names
        assert "multiply" in names
        assert next(s for s in symbols if s.name == "add").type == "function"
        assert next(s for s in symbols if s.name == "multiply").type == "function"

    def test_extracts_const_function_expressions(self, tmp_path: Path):
        (tmp_path / "funcexpr.ts").write_text(
            'export const handler = function handleRequest() {\n'
            '  return "ok";\n'
            '};\n'
        )
        symbols = extract_symbols("funcexpr.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "handler" in names
        assert next(s for s in symbols if s.name == "handler").type == "function"

    def test_extracts_const_variable_declarations(self, tmp_path: Path):
        (tmp_path / "vars.ts").write_text(
            'export const MAX_RETRIES = 3;\n'
            'const BASE_URL = "http://localhost";\n'
        )
        symbols = extract_symbols("vars.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "MAX_RETRIES" in names
        assert "BASE_URL" in names
        assert next(s for s in symbols if s.name == "MAX_RETRIES").type == "variable"
        assert next(s for s in symbols if s.name == "BASE_URL").type == "variable"

    def test_extracts_methods_inside_classes(self, tmp_path: Path):
        (tmp_path / "methods.ts").write_text(
            "class Router {\n"
            "  handle(req: Request) {\n"
            "    return null;\n"
            "  }\n"
            "\n"
            "  async process(data: string) {\n"
            "    return data;\n"
            "  }\n"
            "}\n"
        )
        symbols = extract_symbols("methods.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "handle" in names
        assert "process" in names
        assert next(s for s in symbols if s.name == "handle").type == "method"
        assert next(s for s in symbols if s.name == "process").type == "method"

    def test_assigns_correct_line_numbers(self, tmp_path: Path):
        (tmp_path / "lines.ts").write_text(
            "function first() {\n"
            "  return 1;\n"
            "}\n"
            "\n"
            "function second() {\n"
            "  return 2;\n"
            "}\n"
        )
        symbols = extract_symbols("lines.ts", str(tmp_path))
        first = next(s for s in symbols if s.name == "first")
        second = next(s for s in symbols if s.name == "second")
        assert first.start_line == 1
        assert second.start_line == 5

    def test_does_not_extract_keywords_as_symbols(self, tmp_path: Path):
        (tmp_path / "keywords.ts").write_text(
            "function realFunc() {\n"
            "  if (true) {\n"
            "    for (let i = 0; i < 10; i++) {\n"
            "      while (false) {}\n"
            "    }\n"
            "  }\n"
            "  return 1;\n"
            "}\n"
        )
        symbols = extract_symbols("keywords.ts", str(tmp_path))
        names = [s.name for s in symbols]
        assert "if" not in names
        assert "for" not in names
        assert "while" not in names
        assert "realFunc" in names

    # --- Python ---

    def test_extracts_python_def_and_class_declarations(self, tmp_path: Path):
        (tmp_path / "module.py").write_text(
            "def greet(name):\n"
            '    return f"Hello {name}"\n'
            "\n"
            "class UserService:\n"
            "    def get_user(self):\n"
            "        return None\n"
            "\n"
            "def process():\n"
            "    pass\n"
        )
        symbols = extract_symbols("module.py", str(tmp_path))
        names = [s.name for s in symbols]
        assert "greet" in names
        assert "UserService" in names
        assert "get_user" in names
        assert "process" in names
        assert next(s for s in symbols if s.name == "greet").type == "function"
        assert next(s for s in symbols if s.name == "UserService").type == "class"
        assert next(s for s in symbols if s.name == "get_user").type == "method"

    # --- Go ---

    def test_extracts_go_func_and_type_struct_declarations(self, tmp_path: Path):
        (tmp_path / "main.go").write_text(
            "package main\n"
            "\n"
            "func main() {\n"
            '    fmt.Println("hello")\n'
            "}\n"
            "\n"
            "type Server struct {\n"
            "    Host string\n"
            "    Port int\n"
            "}\n"
            "\n"
            "func (s *Server) Start() {\n"
            "    // start\n"
            "}\n"
            "\n"
            "type Handler interface {\n"
            "    Handle()\n"
            "}\n"
        )
        symbols = extract_symbols("main.go", str(tmp_path))
        names = [s.name for s in symbols]
        assert "main" in names
        assert "Server" in names
        assert "Start" in names
        assert "Handler" in names
        assert next(s for s in symbols if s.name == "main").type == "function"
        assert next(s for s in symbols if s.name == "Server").type == "class"
        assert next(s for s in symbols if s.name == "Start").type == "function"
        assert next(s for s in symbols if s.name == "Handler").type == "type"

    # --- Rust ---

    def test_extracts_rust_fn_struct_and_trait_declarations(self, tmp_path: Path):
        (tmp_path / "lib.rs").write_text(
            "pub fn initialize() {\n"
            "    // init\n"
            "}\n"
            "\n"
            "pub struct Config {\n"
            "    pub host: String,\n"
            "}\n"
            "\n"
            "pub trait Service {\n"
            "    fn run(&self);\n"
            "}\n"
            "\n"
            "async fn fetch_data() {\n"
            "    // fetch\n"
            "}\n"
        )
        symbols = extract_symbols("lib.rs", str(tmp_path))
        names = [s.name for s in symbols]
        assert "initialize" in names
        assert "Config" in names
        assert "Service" in names
        assert "fetch_data" in names
        assert next(s for s in symbols if s.name == "initialize").type == "function"
        assert next(s for s in symbols if s.name == "Config").type == "class"
        assert next(s for s in symbols if s.name == "Service").type == "type"
        assert next(s for s in symbols if s.name == "fetch_data").type == "function"


# ---------------------------------------------------------------------------
# find_symbol
# ---------------------------------------------------------------------------


class TestFindSymbol:
    def test_finds_an_existing_symbol_by_name(self, tmp_path: Path):
        (tmp_path / "mod.ts").write_text(
            'export function alpha() {\n'
            '  return "a";\n'
            '}\n'
            '\n'
            'export function beta() {\n'
            '  return "b";\n'
            '}\n'
        )
        result = find_symbol("mod.ts", "beta", str(tmp_path))
        assert result is not None
        assert result.name == "beta"
        assert result.type == "function"
        assert result.start_line == 5

    def test_returns_none_for_a_symbol_that_does_not_exist(self, tmp_path: Path):
        (tmp_path / "mod.ts").write_text(
            "function exists() {\n"
            "  return true;\n"
            "}\n"
        )
        result = find_symbol("mod.ts", "doesNotExist", str(tmp_path))
        assert result is None

    def test_returns_none_for_a_nonexistent_file(self, tmp_path: Path):
        result = find_symbol("nope.ts", "anything", str(tmp_path))
        assert result is None


# ---------------------------------------------------------------------------
# verify_range
# ---------------------------------------------------------------------------


class TestVerifyRange:
    def test_returns_true_when_range_contains_specified_symbol(self, tmp_path: Path):
        (tmp_path / "code.ts").write_text(
            "const x = 1;\n"
            "function doSomething() {\n"
            "  return x + 1;\n"
            "}\n"
            "const y = 2;\n"
        )
        assert verify_range("code.ts", 2, 4, "doSomething", str(tmp_path)) is True

    def test_returns_false_when_range_does_not_contain_specified_symbol(self, tmp_path: Path):
        (tmp_path / "code.ts").write_text(
            "const x = 1;\n"
            "function doSomething() {\n"
            "  return x + 1;\n"
            "}\n"
            "const y = 2;\n"
        )
        assert verify_range("code.ts", 1, 1, "doSomething", str(tmp_path)) is False

    def test_returns_true_when_no_symbol_specified_and_range_exists(self, tmp_path: Path):
        (tmp_path / "code.ts").write_text(
            "line one\n"
            "line two\n"
            "line three\n"
        )
        assert verify_range("code.ts", 1, 3, None, str(tmp_path)) is True

    def test_returns_false_for_a_nonexistent_file(self, tmp_path: Path):
        assert verify_range("missing.ts", 1, 5, "anything", str(tmp_path)) is False

    def test_returns_true_when_symbol_appears_anywhere_in_range(self, tmp_path: Path):
        (tmp_path / "multi.ts").write_text(
            "// header comment\n"
            "// more comments\n"
            "export function targetSymbol() {\n"
            "  return 42;\n"
            "}\n"
        )
        assert verify_range("multi.ts", 1, 5, "targetSymbol", str(tmp_path)) is True
