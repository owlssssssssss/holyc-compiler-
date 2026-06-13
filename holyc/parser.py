from __future__ import annotations

from typing import List, Optional, Union

from . import ast
from .tokens import Token, TokenKind


class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        super().__init__(f"Parse error at {token.line}:{token.col}: {message}")
        self.token = token


class Parser:
    TYPE_TOKENS = {
        TokenKind.I8, TokenKind.U8, TokenKind.I16, TokenKind.U16,
        TokenKind.I32, TokenKind.U32, TokenKind.I64, TokenKind.U64,
        TokenKind.F64, TokenKind.BOOL, TokenKind.U0, TokenKind.REG,
    }
    REG_TYPES = {
        "Reg", "RegI8", "RegU8", "RegI16", "RegU16", "RegI32", "RegU32",
        "RegI64", "RegU64", "RegF64",
    }

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.class_names: set[str] = set()
        self.union_names: set[str] = set()

    def parse(self) -> ast.Program:
        items: List[Union[ast.ClassDef, ast.UnionDef, ast.FunctionDef, ast.GlobalVar]] = []
        self.class_names = set()
        self.union_names = set()
        while not self._check(TokenKind.EOF):
            pub = self._match(TokenKind.PUBLIC)
            if self._check(TokenKind.CLASS):
                items.append(self._parse_class())
            elif self._check(TokenKind.UNION):
                items.append(self._parse_union())
            elif self._check_type():
                item = self._parse_global_or_func()
                if pub and hasattr(item, "is_public"):
                    item.is_public = True
                items.append(item)
            else:
                raise ParseError("Expected class, union, type, or end of file", self._current())
        return ast.Program(items)

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        tok = self._current()
        if tok.kind != TokenKind.EOF:
            self.pos += 1
        return tok

    def _match(self, kind: TokenKind) -> bool:
        if self._check(kind):
            self._advance()
            return True
        return False

    def _check(self, kind: TokenKind) -> bool:
        return self._current().kind == kind

    def _check_type(self) -> bool:
        if self._current().kind in self.TYPE_TOKENS:
            return True
        if self._current().kind == TokenKind.IDENT:
            n = self._current().value
            return n in self.class_names or n in self.union_names
        return False

    def _expect(self, kind: TokenKind, msg: str) -> Token:
        if not self._check(kind):
            raise ParseError(msg, self._current())
        return self._advance()

    def _parse_type(self) -> ast.TypeNode:
        if not self._check_type():
            raise ParseError("Expected type", self._current())
        base_tok = self._advance()
        base = base_tok.value
        is_register = base in self.REG_TYPES
        pointer_depth = 0
        while self._match(TokenKind.STAR):
            pointer_depth += 1
        is_array = False
        array_size = None
        if self._match(TokenKind.LBRACKET):
            if not self._check(TokenKind.RBRACKET):
                array_size = self._parse_expr()
            self._expect(TokenKind.RBRACKET, "Expected ]")
            is_array = True
        return ast.TypeNode(base, pointer_depth, is_array, array_size, is_register)

    def _parse_class(self) -> ast.ClassDef:
        self._expect(TokenKind.CLASS, "Expected 'class'")
        name = self._expect(TokenKind.IDENT, "Expected class name").value
        self._expect(TokenKind.LBRACE, "Expected '{'")
        fields = self._parse_fields()
        self._advance()
        self._match(TokenKind.SEMI)
        self.class_names.add(name)
        return ast.ClassDef(name, fields)

    def _parse_union(self) -> ast.UnionDef:
        self._expect(TokenKind.UNION, "Expected 'union'")
        name = self._expect(TokenKind.IDENT, "Expected union name").value
        self._expect(TokenKind.LBRACE, "Expected '{'")
        fields = self._parse_fields()
        self._advance()
        self._match(TokenKind.SEMI)
        self.union_names.add(name)
        return ast.UnionDef(name, fields)

    def _parse_fields(self) -> List[ast.FieldDecl]:
        fields: List[ast.FieldDecl] = []
        while not self._check(TokenKind.RBRACE):
            if self._match(TokenKind.PUBLIC):
                pass
            typ = self._parse_type()
            fname = self._expect(TokenKind.IDENT, "Expected field name").value
            self._expect(TokenKind.SEMI, "Expected ';' after field")
            fields.append(ast.FieldDecl(typ, fname))
        return fields

    def _parse_global_or_func(self) -> Union[ast.FunctionDef, ast.GlobalVar]:
        ret_type = self._parse_type()
        name = self._expect(TokenKind.IDENT, "Expected name").value
        if self._match(TokenKind.LPAREN):
            params = self._parse_params()
            self._expect(TokenKind.RPAREN, "Expected ')'")
            self._expect(TokenKind.LBRACE, "Expected '{'")
            body = self._parse_block_stmts()
            return ast.FunctionDef(ret_type, name, params, body)
        init = None
        if self._match(TokenKind.EQ):
            init = self._parse_expr()
        self._expect(TokenKind.SEMI, "Expected ';'")
        return ast.GlobalVar(ret_type, name, init)

    def _parse_params(self) -> List[ast.Param]:
        params: List[ast.Param] = []
        if self._check(TokenKind.RPAREN):
            return params
        while True:
            typ = self._parse_type()
            name = self._expect(TokenKind.IDENT, "Expected parameter name").value
            params.append(ast.Param(typ, name))
            if not self._match(TokenKind.COMMA):
                break
        return params

    def _parse_block_stmts(self) -> List[ast.Stmt]:
        stmts: List[ast.Stmt] = []
        while not self._check(TokenKind.RBRACE) and not self._check(TokenKind.EOF):
            stmts.append(self._parse_stmt())
        self._expect(TokenKind.RBRACE, "Expected '}'")
        return stmts

    def _parse_stmt(self) -> ast.Stmt:
        if self._match(TokenKind.PUBLIC):
            pass

        if self._check(TokenKind.IDENT) and self._peek(1).kind == TokenKind.COLON:
            name = self._advance().value
            self._expect(TokenKind.COLON, "Expected ':'")
            return ast.Label(name)

        if self._check_type():
            return self._parse_var_decl()
        if self._match(TokenKind.IF):
            return self._parse_if()
        if self._match(TokenKind.WHILE):
            return self._parse_while()
        if self._match(TokenKind.DO):
            return self._parse_do_while()
        if self._match(TokenKind.FOR):
            return self._parse_for()
        if self._match(TokenKind.SWITCH):
            return self._parse_switch()
        if self._match(TokenKind.GOTO):
            label = self._expect(TokenKind.IDENT, "Expected label").value
            self._expect(TokenKind.SEMI, "Expected ';' after goto")
            return ast.Goto(label)
        if self._match(TokenKind.ASM):
            return self._parse_asm()
        if self._match(TokenKind.RETURN):
            val = None if self._check(TokenKind.SEMI) else self._parse_expr()
            self._expect(TokenKind.SEMI, "Expected ';' after return")
            return ast.Return(val)
        if self._match(TokenKind.BREAK):
            self._expect(TokenKind.SEMI, "Expected ';' after break")
            return ast.Break()
        if self._match(TokenKind.CONTINUE):
            self._expect(TokenKind.SEMI, "Expected ';' after continue")
            return ast.Continue()
        if self._match(TokenKind.LBRACE):
            return ast.Block(self._parse_block_stmts())
        if self._match(TokenKind.DOLLAR):
            return self._parse_dollar_print()
        if self._check(TokenKind.STRING):
            s = self._advance()
            self._expect(TokenKind.SEMI, "Expected ';' after string statement")
            return ast.Print([ast.StringLit(s.value)])

        return self._parse_expr_or_assign_stmt()

    def _parse_var_decl(self) -> ast.VarDecl:
        typ = self._parse_type()
        name = self._expect(TokenKind.IDENT, "Expected variable name").value
        init = None
        if self._match(TokenKind.EQ):
            init = self._parse_expr()
        elif self._check(TokenKind.LBRACE):
            init = self._parse_array_init()
        self._expect(TokenKind.SEMI, "Expected ';'")
        return ast.VarDecl(typ, name, init)

    def _parse_array_init(self) -> ast.ArrayInit:
        self._expect(TokenKind.LBRACE, "Expected '{'")
        elems: List[ast.Expr] = []
        if not self._check(TokenKind.RBRACE):
            while True:
                elems.append(self._parse_expr())
                if not self._match(TokenKind.COMMA):
                    break
        self._expect(TokenKind.RBRACE, "Expected '}'")
        return ast.ArrayInit(elems)

    def _parse_if(self) -> ast.If:
        self._expect(TokenKind.LPAREN, "Expected '(' after if")
        cond = self._parse_expr()
        self._expect(TokenKind.RPAREN, "Expected ')'")
        then_body = self._parse_stmt_list()
        else_body = None
        if self._match(TokenKind.ELSE):
            else_body = self._parse_stmt_list()
        return ast.If(cond, then_body, else_body)

    def _parse_while(self) -> ast.While:
        self._expect(TokenKind.LPAREN, "Expected '(' after while")
        cond = self._parse_expr()
        self._expect(TokenKind.RPAREN, "Expected ')'")
        return ast.While(cond, self._parse_stmt_list())

    def _parse_do_while(self) -> ast.DoWhile:
        self._expect(TokenKind.LBRACE, "Expected '{' after do")
        body = self._parse_block_stmts()
        self._expect(TokenKind.WHILE, "Expected 'while'")
        self._expect(TokenKind.LPAREN, "Expected '('")
        cond = self._parse_expr()
        self._expect(TokenKind.RPAREN, "Expected ')'")
        self._expect(TokenKind.SEMI, "Expected ';'")
        return ast.DoWhile(body, cond)

    def _parse_for(self) -> ast.For:
        self._expect(TokenKind.LPAREN, "Expected '(' after for")
        if self._check_type():
            typ = self._parse_type()
            name = self._expect(TokenKind.IDENT, "Expected variable name").value
            if self._match(TokenKind.COLON):
                start = self._parse_expr()
                self._expect(TokenKind.DOTDOT, "Expected '..' in range-for")
                end = self._parse_expr()
                self._expect(TokenKind.RPAREN, "Expected ')'")
                body = self._parse_stmt_list()
                return ast.RangeFor(typ, name, start, end, body)
            expr = None
            if self._match(TokenKind.EQ):
                expr = self._parse_expr()
            init: Union[ast.VarDecl, ast.Assign, ast.Expr] = ast.VarDecl(typ, name, expr)
        elif not self._check(TokenKind.SEMI):
            expr = self._parse_expr()
            if self._match(TokenKind.EQ):
                init = ast.Assign(expr, self._parse_expr())
            else:
                init = expr
        else:
            init = None
        self._expect(TokenKind.SEMI, "Expected ';'")
        cond = None if self._check(TokenKind.SEMI) else self._parse_expr()
        self._expect(TokenKind.SEMI, "Expected ';'")
        step = None if self._check(TokenKind.RPAREN) else self._parse_expr()
        self._expect(TokenKind.RPAREN, "Expected ')'")
        return ast.For(init, cond, step, self._parse_stmt_list())

    def _parse_switch(self) -> ast.Switch:
        self._expect(TokenKind.LPAREN, "Expected '(' after switch")
        expr = self._parse_expr()
        self._expect(TokenKind.RPAREN, "Expected ')'")
        self._expect(TokenKind.LBRACE, "Expected '{'")
        cases: List[ast.SwitchCase] = []
        while not self._check(TokenKind.RBRACE):
            if self._match(TokenKind.CASE):
                val = self._parse_expr()
                self._expect(TokenKind.COLON, "Expected ':' after case")
                body = self._parse_switch_body()
                cases.append(ast.SwitchCase(val, body))
            elif self._match(TokenKind.DEFAULT):
                self._expect(TokenKind.COLON, "Expected ':' after default")
                body = self._parse_switch_body()
                cases.append(ast.SwitchCase(None, body, True))
            else:
                raise ParseError("Expected case or default", self._current())
        self._advance()
        return ast.Switch(expr, cases)

    def _parse_switch_body(self) -> List[ast.Stmt]:
        stmts: List[ast.Stmt] = []
        while not self._check(TokenKind.CASE) and not self._check(TokenKind.DEFAULT) and not self._check(TokenKind.RBRACE):
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_asm(self) -> ast.Asm:
        self._expect(TokenKind.LBRACE, "Expected '{' after asm")
        parts: List[str] = []
        while not self._check(TokenKind.RBRACE):
            if self._check(TokenKind.STRING):
                parts.append(self._advance().value)
                self._match(TokenKind.SEMI)
            else:
                raise ParseError("Expected asm string", self._current())
        self._advance()
        return ast.Asm("\n".join(parts))

    def _parse_stmt_list(self) -> List[ast.Stmt]:
        if self._match(TokenKind.LBRACE):
            return self._parse_block_stmts()
        return [self._parse_stmt()]

    def _parse_dollar_print(self) -> ast.Print:
        self._expect(TokenKind.LPAREN, "Expected '(' after $")
        args: List[ast.Expr] = []
        if not self._check(TokenKind.RPAREN):
            while True:
                args.append(self._parse_expr())
                if not self._match(TokenKind.COMMA):
                    break
        self._expect(TokenKind.RPAREN, "Expected ')'")
        self._expect(TokenKind.SEMI, "Expected ';'")
        return ast.Print(args)

    def _parse_expr_or_assign_stmt(self) -> ast.Stmt:
        expr = self._parse_expr()
        compound = {
            TokenKind.PLUSEQ: "+", TokenKind.MINUSEQ: "-", TokenKind.STAREQ: "*",
            TokenKind.SLASHEQ: "/", TokenKind.PERCENTEQ: "%",
        }
        for kind, op in compound.items():
            if self._match(kind):
                value = self._parse_expr()
                self._expect(TokenKind.SEMI, "Expected ';'")
                return ast.Assign(expr, ast.Binary(op, expr, value))
        if self._match(TokenKind.EQ):
            value = self._parse_expr()
            self._expect(TokenKind.SEMI, "Expected ';'")
            return ast.Assign(expr, value)
        self._expect(TokenKind.SEMI, "Expected ';'")
        if isinstance(expr, ast.StringLit):
            return ast.Print([expr])
        return ast.ExprStmt(expr)

    def _parse_expr(self) -> ast.Expr:
        return self._parse_ternary()

    def _parse_ternary(self) -> ast.Expr:
        expr = self._parse_assign()
        if self._match(TokenKind.QMARK):
            then_e = self._parse_expr()
            self._expect(TokenKind.COLON, "Expected ':' in ternary")
            else_e = self._parse_ternary()
            return ast.Ternary(expr, then_e, else_e)
        return expr

    def _parse_assign(self) -> ast.Expr:
        expr = self._parse_or()
        if self._match(TokenKind.EQ):
            return ast.Binary("=", expr, self._parse_assign())
        return expr

    def _parse_or(self) -> ast.Expr:
        expr = self._parse_and()
        while self._match(TokenKind.OR):
            expr = ast.Binary("||", expr, self._parse_and())
        return expr

    def _parse_and(self) -> ast.Expr:
        expr = self._parse_bitor()
        while self._match(TokenKind.AND):
            expr = ast.Binary("&&", expr, self._parse_bitor())
        return expr

    def _parse_bitor(self) -> ast.Expr:
        expr = self._parse_bitxor()
        while self._match(TokenKind.PIPE):
            expr = ast.Binary("|", expr, self._parse_bitxor())
        return expr

    def _parse_bitxor(self) -> ast.Expr:
        expr = self._parse_bitand()
        while self._match(TokenKind.CARET):
            expr = ast.Binary("^", expr, self._parse_bitand())
        return expr

    def _parse_bitand(self) -> ast.Expr:
        expr = self._parse_equality()
        while self._match(TokenKind.AMPERSAND):
            expr = ast.Binary("&", expr, self._parse_equality())
        return expr

    def _parse_equality(self) -> ast.Expr:
        expr = self._parse_relational()
        while True:
            if self._match(TokenKind.EQEQ):
                expr = ast.Binary("==", expr, self._parse_relational())
            elif self._match(TokenKind.NEQ):
                expr = ast.Binary("!=", expr, self._parse_relational())
            else:
                break
        return expr

    def _parse_relational(self) -> ast.Expr:
        expr = self._parse_shift()
        while True:
            if self._match(TokenKind.LT):
                expr = ast.Binary("<", expr, self._parse_shift())
            elif self._match(TokenKind.GT):
                expr = ast.Binary(">", expr, self._parse_shift())
            elif self._match(TokenKind.LTE):
                expr = ast.Binary("<=", expr, self._parse_shift())
            elif self._match(TokenKind.GTE):
                expr = ast.Binary(">=", expr, self._parse_shift())
            else:
                break
        return expr

    def _parse_shift(self) -> ast.Expr:
        expr = self._parse_additive()
        while True:
            if self._match(TokenKind.LSHIFT):
                expr = ast.Binary("<<", expr, self._parse_additive())
            elif self._match(TokenKind.RSHIFT):
                expr = ast.Binary(">>", expr, self._parse_additive())
            else:
                break
        return expr

    def _parse_additive(self) -> ast.Expr:
        expr = self._parse_multiplicative()
        while True:
            if self._match(TokenKind.PLUS):
                expr = ast.Binary("+", expr, self._parse_multiplicative())
            elif self._match(TokenKind.MINUS):
                expr = ast.Binary("-", expr, self._parse_multiplicative())
            else:
                break
        return expr

    def _parse_multiplicative(self) -> ast.Expr:
        expr = self._parse_unary()
        while True:
            if self._match(TokenKind.STAR):
                expr = ast.Binary("*", expr, self._parse_unary())
            elif self._match(TokenKind.SLASH):
                expr = ast.Binary("/", expr, self._parse_unary())
            elif self._match(TokenKind.PERCENT):
                expr = ast.Binary("%", expr, self._parse_unary())
            else:
                break
        return expr

    def _parse_unary(self) -> ast.Expr:
        if self._match(TokenKind.SIZEOF):
            return self._parse_sizeof()
        if self._match(TokenKind.PLUSPLUS):
            return ast.Unary("++pre", self._parse_unary())
        if self._match(TokenKind.MINUSMINUS):
            return ast.Unary("--pre", self._parse_unary())
        if self._match(TokenKind.BANG):
            return ast.Unary("!", self._parse_unary())
        if self._match(TokenKind.TILDE):
            return ast.Unary("~", self._parse_unary())
        if self._match(TokenKind.MINUS):
            return ast.Unary("-", self._parse_unary())
        if self._match(TokenKind.PLUS):
            return ast.Unary("+", self._parse_unary())
        if self._match(TokenKind.AMPERSAND):
            return ast.Unary("&", self._parse_unary())
        if self._match(TokenKind.STAR):
            return ast.Unary("*", self._parse_unary())
        return self._parse_postfix()

    def _parse_sizeof(self) -> ast.Sizeof:
        self._expect(TokenKind.LPAREN, "Expected '(' after sizeof")
        if self._check_type():
            typ = self._parse_type()
            self._expect(TokenKind.RPAREN, "Expected ')'")
            return ast.Sizeof(type=typ)
        expr = self._parse_expr()
        self._expect(TokenKind.RPAREN, "Expected ')'")
        return ast.Sizeof(expr=expr)

    def _parse_postfix(self) -> ast.Expr:
        expr = self._parse_primary()
        while True:
            if self._match(TokenKind.LBRACKET):
                index = self._parse_expr()
                self._expect(TokenKind.RBRACKET, "Expected ']'")
                expr = ast.Index(expr, index)
            elif self._match(TokenKind.DOT):
                field = self._expect(TokenKind.IDENT, "Expected field name").value
                expr = ast.Member(expr, field, False)
            elif self._match(TokenKind.ARROW):
                field = self._expect(TokenKind.IDENT, "Expected field name").value
                expr = ast.Member(expr, field, True)
            elif self._match(TokenKind.PLUSPLUS):
                expr = ast.Unary("++post", expr)
            elif self._match(TokenKind.MINUSMINUS):
                expr = ast.Unary("--post", expr)
            elif self._match(TokenKind.LPAREN):
                args: List[ast.Expr] = []
                if not self._check(TokenKind.RPAREN):
                    while True:
                        args.append(self._parse_expr())
                        if not self._match(TokenKind.COMMA):
                            break
                self._expect(TokenKind.RPAREN, "Expected ')'")
                expr = ast.Call(expr, args)
            else:
                break
        return expr

    def _parse_primary(self) -> ast.Expr:
        if self._match(TokenKind.INT):
            return ast.IntLit(int(self._peek(-1).value, 0))
        if self._match(TokenKind.FLOAT):
            return ast.FloatLit(float(self._peek(-1).value))
        if self._match(TokenKind.STRING):
            return ast.StringLit(self._peek(-1).value)
        if self._match(TokenKind.CHAR):
            return ast.CharLit(self._peek(-1).value)
        if self._match(TokenKind.TRUE):
            return ast.BoolLit(True)
        if self._match(TokenKind.FALSE):
            return ast.BoolLit(False)
        if self._match(TokenKind.NULL):
            return ast.NullLit()
        if self._match(TokenKind.LBRACE):
            return self._parse_array_init()
        if self._match(TokenKind.LPAREN):
            expr = self._parse_expr()
            self._expect(TokenKind.RPAREN, "Expected ')'")
            return expr
        if self._check_type():
            typ = self._parse_type()
            self._expect(TokenKind.LPAREN, "Expected '(' for cast")
            inner = self._parse_expr()
            self._expect(TokenKind.RPAREN, "Expected ')'")
            return ast.Cast(typ, inner)
        if self._match(TokenKind.IDENT):
            return ast.Ident(self._peek(-1).value)
        raise ParseError("Expected expression", self._current())