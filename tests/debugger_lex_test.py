# ------------------------------------------------------------
# calclex.py
#
# tokenizer for a simple expression evaluator for
# numbers and +,-,*,/
# ------------------------------------------------------------
import ply.lex as lex

# precedence based on python operator precedence
precedence_groups = [
    ('LPAREN',),
    ('OP_LOGICAL_OR',),
    ('OP_LOGICAL_AND',),
    ('unary', 'OP_LOGICAL_NOT',),
    ('OP_LT', 'OP_LE', 'OP_GT', 'OP_GE', 'OP_NE', 'OP_EQ',),
    ('OP_BITWISE_OR',),
    ('OP_BITWISE_AND',),
    ('unary', 'OP_BITWISE_NOT',),
    ('OP_LSHIFT', 'OP_RSHIFT',),
    ('OP_PLUS', 'OP_MINUS',),
    ('OP_MULT', 'OP_DIV',),
    ('unary', 'OP_UPLUS', 'OP_UMINUS',),
    ('OP_EXP',),
]
token_unary_replacement = {
    'OP_MINUS': 'OP_UMINUS',
    'OP_PLUS': 'OP_UPLUS',
}

op_tokens = set()
precedence = {}
unary = set()
precedence_level = 1
for group in precedence_groups:
    is_unary = group[0] == 'unary'
    if is_unary:
        group = group[1:]
    for token_name in group:
        if is_unary:
            unary.add(token_name)
        op_tokens.add(token_name)
        precedence[token_name] = precedence_level
    precedence_level += 1


# List of token names.   This is always required
tokens = ['REG', 'NUMBER', 'RPAREN'] + list(op_tokens)

# Regular expression rules for simple tokens
t_OP_PLUS    = r'\+'
t_OP_MINUS   = r'-'
t_OP_MULT    = r'\*'
t_OP_DIV     = r'/'
t_OP_EXP     = r'\*\*'
t_OP_BITWISE_OR = r'\|'
t_OP_BITWISE_AND = r'\&'
t_OP_BITWISE_NOT = r'~'
t_OP_LOGICAL_OR = r'or'
t_OP_LOGICAL_AND = r'and'
t_OP_LOGICAL_NOT = r'not'
t_OP_LSHIFT  = r'<<'
t_OP_RSHIFT  = r'>>'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'

# Define as a function because simple token regexes don't respect file order
def t_REG(t):
    r'[axy]|pc|sp'
    return t

# A regular expression rule with some action code
def t_NUMBER(t):
    r'\$?[a-fA-F\d]+'
    t.value = int(t.value, 16)
    return t

# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()


# From https://stackoverflow.com/questions/17254080/
#
#  If an operator is the first thing in your expression, or comes after another
#  operator, or comes after a left parenthesis, then it's an unary operator.
#  You have to use other symbols for unary operators in your output string,
#  because otherwise it is not possible to distinguish between binary and unary
#  variants in the postfix notation.


def to_postfix(tokens):
    operands = []
    postfix = []
    last_tok = None
    for tok in tokens:
        if tok.type == "REG" or tok.type == "NUMBER":
            postfix.append(tok)
        elif tok.type == "LPAREN":
            operands.append(tok)
        elif tok.type == "RPAREN":
            top_token = operands.pop()
            while top_token.type != "LPAREN":
                postfix.append(top_token)
                top_token = operands.pop()
        else:
            if tok.type in token_unary_replacement:
                if last_tok is None or last_tok.type in op_tokens or last_tok.type == "LPAREN":
                    tok.type = token_unary_replacement[tok.type]
            while operands and precedence[operands[-1].type] >= precedence[tok.type]:
                postfix.append(operands.pop())
            operands.append(tok)
        last_tok = tok

    while operands:
        postfix.append(operands.pop())
    return postfix


if __name__ == "__main__":
    # Test it out
    data = '''
    -~5
    a + -- 4
    a + -+- ~4
    a + 10 +-+x
    a + 10 + (not (a or b))
    a + - (b + c)
    a + 10 + -x + -y + (4*8)  # evaluates as a + 10 + -x + (-y) + (4*8)
    a + 10 + -x + ~y + (4*8)  # Notice the difference; ~ has lower precedence than +. evaluates as a + 10 + -x + ~(y + (4*8))
    '''

    # Give the lexer some input
    for line in data.splitlines():
        if "#" in line:
            line, _ = line.split("#", 1)
        line = line.strip()
        if not line: continue
        lexer.input(line)

        # Tokenize
        tokens = []
        print("infix:")
        while True:
            tok = lexer.token()
            if not tok: 
                break      # No more input
            print(tok, tok.type, type(tok.type), tok.value)
            tokens.append(tok)
        print("postfix:",)
        print("\n".join([str(tok) for tok in to_postfix(tokens)]))
