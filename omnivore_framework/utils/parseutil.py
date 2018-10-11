# pyparsing code based on original code arith.py by Paul McGuire, modified by
# Glenn Linderman, licensed under the pyparsing license arith.py from:
#
# http://pyparsing.wikispaces.com/file/view/arith.py/241810293/arith.py
import numpy as np

from pyparsing import Word, nums, hexnums, alphas, Combine, oneOf, Optional, \
    opAssoc, operatorPrecedence, ParseException, ParserElement, Literal, Regex, pyparsing_common

ParserElement.enablePackrat()


class EvalConstant():
    "Class to evaluate a parsed constant or variable"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_):
        v = self.value
        if v in vars_:
            return vars_[v]
        else:
            if v.startswith("$"):
                return int(v[1:], 16)
            elif v.startswith("0x"):
                return int(v[2:], 16)
            else:
                return int(v)


class EvalSignOp():
    "Class to evaluate expressions with a leading + or - sign"

    def __init__(self, tokens):
        self.sign, self.value = tokens[0]

    def eval(self, vars_):
        mult = {'+':1, '-':-1}[self.sign]
        return mult * self.value.eval(vars_)


def operatorOperands(tokenlist):
    "generator to extract operators and operands in pairs"
    it = iter(tokenlist)
    while 1:
        try:
            o1 = next(it)
            o2 = next(it)
            yield (o1, o2)
        except StopIteration:
            break


class EvalMultOp():
    "Class to evaluate multiplication and division expressions"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        prod = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            if op == '*':
                prod *= val.eval(vars_)
            if op == '/':
                prod /= val.eval(vars_)
            if op == '//':
                prod //= val.eval(vars_)
            if op == '%':
                prod %= val.eval(vars_)
        return prod


class EvalAddOp():
    "Class to evaluate addition and subtraction expressions"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        sum = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            if op == '+':
                sum += val.eval(vars_)
            if op == '-':
                sum -= val.eval(vars_)
        return sum


class EvalBitwiseAndOp():
    "Class to evaluate addition and subtraction expressions"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        val1 = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            val2 = val.eval(vars_)
            val1 = val1 & val2
        return val1


class EvalBitwiseOrOp():
    "Class to evaluate addition and subtraction expressions"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        val1 = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            val2 = val.eval(vars_)
            val1 = val1 | val2
        return val1


class EvalLogicalAndOp():
    "Class to evaluate addition and subtraction expressions"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        val1 = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            val2 = val.eval(vars_)
            val1 = np.logical_and(val1, val2)
        return val1


class EvalLogicalOrOp():
    "Class to evaluate addition and subtraction expressions"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        val1 = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            val2 = val.eval(vars_)
            val1 = np.logical_or(val1, val2)
        return val1


class EvalComparisonOp():
    "Class to evaluate comparison expressions"
    opMap = {
        "<" : lambda a,b : a < b,
        "<=" : lambda a,b : a <= b,
        ">" : lambda a,b : a > b,
        ">=" : lambda a,b : a >= b,
        "==" : lambda a,b : a == b,
        "!=" : lambda a,b : a != b,
        "<>" : lambda a,b : a != b,
        }

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_ ):
        val1 = self.value[0].eval(vars_)
        if type(val1) is np.ndarray:
            for op,val in operatorOperands(self.value[1:]):
                fn = self.opMap[op]
                val2 = val.eval(vars_)
                val1 = fn(val1, val2)
            return val1
        else:
            for op,val in operatorOperands(self.value[1:]):
                fn = self.opMap[op]
                val2 = val.eval(vars_)
                if not fn(val1,val2):
                    break
                val1 = val2
            else:
                return True
            return False


class NumpyIntExpression():
    integer = Word(nums)
    hexint = Combine(oneOf('0x $') + Word(hexnums))

    variable = Word(alphas)
    operand = hexint | integer | variable

    signop = oneOf('+ -')
    multop = oneOf('* / // %')
    plusop = oneOf('+ -')
    bitwiseandop = Literal('&')
    bitwiseorop = Literal('|')
    logicalandop = oneOf('and &&')
    logicalorop = oneOf('or ||')
    comparisonop = oneOf("< <= > >= == != <>")

    # use parse actions to attach EvalXXX constructors to sub-expressions
    operand.setParseAction(EvalConstant)
    arith_expr = operatorPrecedence(operand,
        [(signop, 1, opAssoc.RIGHT, EvalSignOp),
         (multop, 2, opAssoc.LEFT, EvalMultOp),
         (plusop, 2, opAssoc.LEFT, EvalAddOp),
         (bitwiseandop, 2, opAssoc.LEFT, EvalBitwiseAndOp),
         (bitwiseorop, 2, opAssoc.LEFT, EvalBitwiseOrOp),
         (comparisonop, 2, opAssoc.LEFT, EvalComparisonOp),
         (logicalandop, 2, opAssoc.LEFT, EvalLogicalAndOp),
         (logicalorop, 2, opAssoc.LEFT, EvalLogicalOrOp),
         ])

    def __init__(self, vars_={}):
        self.vars_ = vars_

    def setvars(self, vars_):
        self.vars_ = vars_

    def setvar( var, val ):
        self.vars_[ var ] = val

    def eval( self, strExpr ):
        ret = self.arith_expr.parseString( strExpr, parseAll=True)[0]
        result = ret.eval( self.vars_ )
        return result


class EvalFloatConstant():
    "Class to evaluate a parsed constant or variable"

    def __init__(self, tokens):
        self.value = tokens[0]

    def eval(self, vars_):
        v = self.value
        if v in vars_:
            return vars_[v]
        else:
            return float(v)


class NumpyFloatExpression():
    variable = Word(alphas)
    leading_dot_float = Regex(r'\.\d+')
    operand = leading_dot_float | pyparsing_common.number | variable

    signop = oneOf('+ -')
    multop = oneOf('* / // %')
    plusop = oneOf('+ -')
    andop = oneOf('and &')
    orop = oneOf('or |')
    comparisonop = oneOf("< <= > >= == != <>")

    # use parse actions to attach EvalXXX constructors to sub-expressions
    operand.setParseAction(EvalFloatConstant)
    arith_expr = operatorPrecedence(operand,
        [(signop, 1, opAssoc.RIGHT, EvalSignOp),
         (multop, 2, opAssoc.LEFT, EvalMultOp),
         (plusop, 2, opAssoc.LEFT, EvalAddOp),
         (comparisonop, 2, opAssoc.LEFT, EvalComparisonOp),
         (andop, 2, opAssoc.LEFT, EvalLogicalAndOp),
         (orop, 2, opAssoc.LEFT, EvalLogicalOrOp),
         ])

    def __init__(self, vars_={}):
        self.vars_ = vars_

    def setvars(self, vars_):
        self.vars_ = vars_

    def setvar( var, val ):
        self.vars_[ var ] = val

    def eval( self, strExpr ):
        ret = self.arith_expr.parseString( strExpr, parseAll=True)[0]
        result = ret.eval( self.vars_ )
        return result


if __name__=='__main__':
    a = np.arange(256*256)
    b = np.arange(256*256)
    f = np.linspace(0, 1, 101, dtype=np.float32)
    v = {"a": a, "b": b, "f": f}
    arith = NumpyIntExpression(v)
    tests = [
        ("a > 3", a > 3),
        ("b > 8", b > 8),
        ("(a > 3) && (a > 5)", a > 5),
        ("a > 3 && a > 5", a > 5),
        ("(a > 3) && (a < 100)", np.logical_and((a > 3), (a < 100))),
        ("a > 3 && a < 100", np.logical_and((a > 3), (a < 100))),
        ("(a & 7)", a & 7),
        ("((a & 7) > 3)", (a & 7) > 3),
        ("((a & 7) > 3) && (a > 5)", np.logical_and(((a & 7) > 3), (a > 5))),
        ("((a & 7) > 3) || (a > 25)", np.logical_or(((a & 7) > 3), (a > 25))),
        ("(a > 1000) || (a < 20)", np.logical_or((a > 1000), (a < 20))),
        ("a > 1000 || a < 20", np.logical_or((a > 1000), (a < 20))),
        ]
    for test, expected in tests:
        result = arith.eval(test)
        correct = (expected == result).all()
        if correct:
            print((test, "correct!"))
        else:
            print((test, "FAILED", expected, result))

    arith = NumpyFloatExpression(v)
    tests = [
        ("f > 3", f > 3),
        ("f > 0.3", f > .3),
        ("f > .3", f > .3),
        ]
    for test, expected in tests:
        result = arith.eval(test)
        correct = (expected == result).all()
        if correct:
            print((test, "correct!"))
        else:
            print((test, "FAILED", expected, result))
