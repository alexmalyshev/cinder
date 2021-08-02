from compiler.static.errors import TypedSyntaxError
from re import escape

from __static__ import Array, int64
from cinder import freeze_type

from .common import StaticTestBase

from .common import StaticTestBase


class StaticObjCreationTests(StaticTestBase):
    def test_new_and_init(self):
        codestr = """
            class C:
                def __new__(cls, a):
                    return object.__new__(cls)
                def __init__(self, a):
                    self.a = a

            X = 0
            def g() -> int:
                global X
                X += 1
                return 1

            def f() -> C:
                return C(g())
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            f()
            self.assertEqual(mod["X"], 1)

    def test_object_init_and_new(self):
        codestr = """
            class C:
                pass

            def f(x: int) -> C:
                return C(x)
        """
        with self.assertRaisesRegex(
            TypedSyntaxError,
            escape("<module>.C() takes no arguments"),
        ):
            self.compile(codestr)

    def test_init(self):
        codestr = """
            class C:

                def __init__(self, a: int) -> None:
                    self.value = a

            def f(x: int) -> C:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(42).value, 42)

    def test_init_primitive(self):
        codestr = """
            from __static__ import int64
            class C:

                def __init__(self, a: int64) -> None:
                    self.value: int64 = a

            def f(x: int64) -> C:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            init = mod["C"].__init__
            self.assertInBytecode(init, "LOAD_LOCAL")
            self.assertInBytecode(init, "STORE_FIELD")
            self.assertEqual(f(42).value, 42)

    def test_new_primitive(self):
        codestr = """
            from __static__ import int64
            class C:
                value: int64
                def __new__(cls, a: int64) -> "C":
                    res: C = object.__new__(cls)
                    res.value = a
                    return res

            def f(x: int64) -> C:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            init = mod["C"].__new__
            self.assertInBytecode(init, "LOAD_LOCAL")
            self.assertInBytecode(init, "STORE_FIELD")
            self.assertEqual(f(42).value, 42)

    def test_init_frozen_type(self):
        codestr = """
            class C:

                def __init__(self, a: int) -> None:
                    self.value = a

            def f(x: int) -> C:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            C = mod["C"]
            freeze_type(C)
            f = mod["f"]
            self.assertEqual(f(42).value, 42)

    def test_init_unknown_base(self):
        codestr = """
            from re import Scanner
            class C(Scanner):
                pass

            def f(x: int) -> C:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            # Unknown base class w/ no overrides should always be CALL_FUNCTION
            self.assertInBytecode(f, "CALL_FUNCTION")

    def test_init_wrong_type(self):
        codestr = """
            class C:

                def __init__(self, a: int) -> None:
                    self.value = a

            def f(x: str) -> C:
                return C(x)
        """
        with self.assertRaisesRegex(
            TypedSyntaxError,
            "type mismatch: str received for positional arg 'a', expected int",
        ):
            self.compile(codestr)

    def test_init_extra_arg(self):
        codestr = """
            class C:

                def __init__(self, a: int) -> None:
                    self.value = a

            def f(x: int) -> C:
                return C(x, 42)
        """
        with self.assertRaisesRegex(
            TypedSyntaxError,
            escape(
                "Mismatched number of args for function <module>.C.__init__. Expected 2, got 3"
            ),
        ):
            self.compile(codestr)

    def test_new(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int) -> "C":
                    res = object.__new__(cls)
                    res.value = a
                    return res

            def f(x: int) -> C:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(42).value, 42)

    def test_new_wrong_type(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int) -> "C":
                    res = object.__new__(cls)
                    res.value = a
                    return res

            def f(x: str) -> C:
                return C(x)
        """
        with self.assertRaisesRegex(
            TypedSyntaxError,
            "type mismatch: str received for positional arg 'a', expected int",
        ):
            self.compile(codestr)

    def test_new_object(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int) -> object:
                    res = object.__new__(cls)
                    res.value = a
                    return res
                def __init__(self, a: int):
                    self.value = 100

            def f(x: int) -> object:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(42).value, 100)

    def test_new_dynamic(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int):
                    res = object.__new__(cls)
                    res.value = a
                    return res
                def __init__(self, a: int):
                    self.value = 100

            def f(x: int) -> object:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(42).value, 100)

    def test_new_odd_ret_type(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int) -> int:
                    return 42

            def f(x: int) -> int:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(42), 42)

    def test_new_odd_ret_type_no_init(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int) -> int:
                    return 42
                def __init__(self, *args) -> None:
                    raise Exception("no way")

            def f(x: int) -> int:
                return C(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(42), 42)

    def test_new_odd_ret_type_error(self):
        codestr = """
            class C:
                value: int
                def __new__(cls, a: int) -> int:
                    return 42

            def f(x: int) -> str:
                return C(x)
        """
        with self.assertRaisesRegex(
            TypedSyntaxError, "return type must be str, not int"
        ):
            self.compile(codestr)

    def test_array_new(self):
        codestr = """
            from __static__ import Array, int64

            def f() -> Array[int64]:
                return Array[int64].__new__(Array[int64])
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertEqual(f(), Array[int64](()))

    def test_class_init_kw(self):
        codestr = """
            class C:
                def __init__(self, x: str):
                    self.x: str = x

            def f():
                x = C(x='abc')
                return x
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertNotInBytecode(f, "CALL_FUNCTION_KW", 1)
            self.assertInBytecode(f, "TP_ALLOC")
            self.assertInBytecode(f, "INVOKE_FUNCTION")
            c = f()
            self.assertEqual(c.x, "abc")

    def test_type_subclass(self):
        codestr = """
            class C(type):
                pass

            def f() -> C:
                return C('foo', (), {})
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            C = mod["C"]
            self.assertEqual(type(f()), C)

    def test_object_new(self):
        codestr = """
            class C(object):
                pass

            def f() -> C:
                return object.__new__(C)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            C = mod["C"]
            self.assertEqual(type(f()), C)

    def test_object_new_wrong_type(self):
        codestr = """
            class C(object):
                pass

            def f() -> C:
                return object.__new__(object)
        """
        with self.assertRaisesRegex(
            TypedSyntaxError,
            "return type must be <module>.C, not object",
        ):
            self.compile(codestr)

    def test_bool_call(self):
        codestr = """
            def f(x) -> bool:
                return bool(x)
        """
        with self.in_module(codestr) as mod:
            f = mod["f"]
            self.assertInBytecode(
                f, "INVOKE_FUNCTION", ((("builtins", "bool", "__new__"), 2))
            )
            self.assertEqual(f(42), True)
            self.assertEqual(f(0), False)
