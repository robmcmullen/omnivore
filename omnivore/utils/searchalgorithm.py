# pyparsing code based on original code arith.py by Paul McGuire, modified by
# Glenn Linderman, licensed under the pyparsing license arith.py from:
#
# http://pyparsing.wikispaces.com/file/view/arith.py/241810293/arith.py
import numpy as np

from pyparsing import Word, nums, hexnums, alphas, Combine, oneOf, Optional, \
    opAssoc, operatorPrecedence, ParseException

from searchutil import BaseSearcher

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
    
class EvalAndOp():
    "Class to evaluate addition and subtraction expressions"
    def __init__(self, tokens):
        self.value = tokens[0]
    def eval(self, vars_ ):
        val1 = self.value[0].eval(vars_)
        for op,val in operatorOperands(self.value[1:]):
            val2 = val.eval(vars_)
            val1 = val1 & val2
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
    
class NumpyExpression():
    integer = Word(nums)
    hexint = Combine(oneOf('0x $') + Word(hexnums))
         
    variable = Word(alphas)
    operand = hexint | integer | variable

    signop = oneOf('+ -')
    multop = oneOf('* / // %')
    plusop = oneOf('+ -')
    andop = oneOf('and &')
    comparisonop = oneOf("< <= > >= == != <>")

    # use parse actions to attach EvalXXX constructors to sub-expressions
    operand.setParseAction(EvalConstant)
    arith_expr = operatorPrecedence(operand,
        [(signop, 1, opAssoc.RIGHT, EvalSignOp),
         (multop, 2, opAssoc.LEFT, EvalMultOp),
         (plusop, 2, opAssoc.LEFT, EvalAddOp),
         (andop, 2, opAssoc.LEFT, EvalAndOp),
         (comparisonop, 2, opAssoc.LEFT, EvalComparisonOp),
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


class AlgorithmSearcher(BaseSearcher):
    def __str__(self):
        return "pyparsing matches: %s" % str(self.matches)
    
    def get_search_text(self, text):
        return text
    
    def get_matches(self, editor):
        s = editor.segment
        a = np.arange(s.start_addr, s.start_addr + len(s))
        b = np.copy(s.data)
        v = {
            'a': np.arange(s.start_addr, s.start_addr + len(s)),
            'b': np.copy(s.data),
            }
        expression = NumpyExpression(v)
        try:
            result = expression.eval(self.search_text)
            matches = s.bool_to_ranges(result)
            return matches
        except ParseException, e:
            raise ValueError(e)


if __name__=='__main__': 
    a = np.arange(256*256)
    b = np.arange(256*256)
    #v = {"a": 5, "b": 10}
    v = {"a": a, "b": b}
    arith = NumpyExpression(v)
    tests = [
        ("a > 3", a > 3),
        ("b > 8", b > 8),
        ("(a > 3) & (a > 5)", a > 5),
        ("(a & 7)", a & 7),
        ("((a & 7) > 3)", (a & 7) > 3),
        ("((a & 7) > 3) & (a > 5)", ((a & 7) > 3) & (a > 5)),
        ]
    for test, expected in tests:
        result = arith.eval(test)
        correct = (expected == result).all()
        if correct:
            print test, "correct!"
        else:
            print test, "FAILED", expected, result
