from dataclasses import dataclass
from typing import AbstractSet, Callable, Hashable

class ParserSyntaxError(ValueError):
    pass

class EscapeError(ParserSyntaxError):
    def __init__(self, s: str, i: int, parsed_args: list[str]) -> None:
        self.s = s
        self.i = i
        self.parsed_args = parsed_args

        super().__init__(s, i, parsed_args)

class UnquotedCharError(ParserSyntaxError):
    def __init__(self, s: str, i: int, parsed_args: list[str]) -> None:
        self.s = s
        self.i = i
        self.parsed_args = parsed_args

        super().__init__(s, i, parsed_args)

class InvalidTokenError(ParserSyntaxError):
    def __init__(self, expected: AbstractSet[str], s: str, i: int) -> None:
        self.expected = expected
        self.s = s
        self.i = i

        super().__init__(s, i)


class DelimiterError(ParserSyntaxError):
    pass

class CommaError(DelimiterError):
    def __init__(self, too_many: bool, s: str, i: int, parsed_args: list[str]) -> None:
        self.too_many = too_many
        self.s = s
        self.i = i
        self.parsed_args = parsed_args

        super().__init__(too_many, s, i, parsed_args)

class GluedKwargs(DelimiterError):
    def __init__(self, s: str, i: int) -> None:
        self.s = s
        self.i = i

        super().__init__(s, i)


class UnclosedError(ParserSyntaxError): 
    pass

class UnclosedQuotesError(UnclosedError):
    def __init__(self, unclosed_arg: str, s: str, parsed_args: list[str]) -> None:
        self.unclosed_arg = unclosed_arg
        self.s = s
        self.parsed_args = parsed_args

        super().__init__(unclosed_arg, s, parsed_args)

class UnclosedListError(UnclosedError):
    def __init__(self, unclosed_args: list[str], s: str) -> None:
        super().__init__(unclosed_args, s)


class ParserValueError(ValueError):
    pass

class KeywordNotUniqueError[TK: Hashable, TV](ParserValueError):
    def __init__(self, keyword: TK, old_new: tuple[TV, TV]) -> None:
        self.keyword = keyword
        self.old_new = old_new

        super().__init__(keyword, old_new)


@dataclass(frozen=True, eq=True, unsafe_hash=True)
class ArgParser[TArgs, TKwargK: Hashable, TKwargV, TKwargs]:
    pre: Callable[[str], str]
    post_args: Callable[[list[str]], TArgs]
    post_kwarg: Callable[[tuple[str, list[str]]], tuple[TKwargK, TKwargV]]
    post_kwargs: Callable[[dict[TKwargK, TKwargV]], TKwargs]
    
    def _parse_args_core(self, s: str) -> list[str]:
        """Guarantees to not modify string (important for exception indexes)."""

        arg: list[str] = []
        args: list[str] = []
        in_escape: bool = False
        in_quotes: bool = False
        comma: bool = True

        for i, c in enumerate(s):
            if not in_quotes:
                if c == ',':
                    if comma:
                        raise CommaError(True, s, i, args)
                    
                    comma = True
                
                elif c == '"':
                    if not comma:
                        raise CommaError(False, s, i, args)
                    
                    in_quotes = True

                elif not c.isspace():
                    raise UnquotedCharError(s, i, args)

            else: 
                if in_escape:
                    if c not in '\\"':
                        raise EscapeError(s, i, args)
                    
                    arg.append(c)
                    in_escape = False
            
                elif c == '\\':
                    if not in_quotes:
                        raise UnquotedCharError(s, i, args)
                
                    in_escape = True
                
                elif c == '"':
                    in_quotes = False
                    comma = False

                    args.append(''.join(arg))
                    arg = []
        
        if in_escape:
            raise EscapeError(s, len(s), args)

        if in_quotes:
            raise UnclosedQuotesError(''.join(arg), s, args)
        
        return args
    
    
    def parse_args(self, s: str) -> TArgs:
        return self.post_args(self._parse_args_core(self.pre(s)))

    def _parse_single_arg_with_rest(self, s: str, force_post_spacing: bool) -> tuple[str, str]:
        assert s == s.rstrip()
        assert s

        arg: list[str] = []
        in_escape: bool = False
        quotes: int = 0
        
        for i, c in enumerate(s):
            match quotes:
                case 0:
                    if c == '"':
                        quotes = 1
                    elif not c.isspace():
                        raise UnquotedCharError(s, i, [])
                case 1:
                    if in_escape:
                        if c not in '\\"':
                            raise EscapeError(s, i, arg)
                        arg.append(c)
                        in_escape = False
                    
                    elif c == '\\':
                        in_escape = True
                    elif c == '"':
                        quotes = 2
                    else:
                        arg.append(c)
                    
                case 2:
                    if not c.isspace():
                        if force_post_spacing and not s[i - 1].isspace():
                            raise GluedKwargs(s, i)
                        
                        return (s[i:], ''.join(arg))
        
        assert quotes != 0

        if quotes == 1:
            raise UnclosedQuotesError(''.join(arg), s, [])
        
        return ("", ''.join(arg))
                

    def _parse_kw_name(self, s: str) -> tuple[str, str]:
        assert s == s.rstrip()
        
        s, arg = self._parse_single_arg_with_rest(s, False)

        if not s.startswith('='):
            raise InvalidTokenError({'='}, s, 0)
        
        return (s[1:].rstrip(), ''.join(arg))
    
    def _parse_kw_value(self, s: str) -> tuple[str, list[str]]:
        if not s.startswith('['):
            if not s.startswith('"'):
                raise InvalidTokenError({'[', '"'}, s, 0)
            
            s, arg = self._parse_single_arg_with_rest(s, True)

            return s, [arg]
    
        s = s[1:]

        try:
            unclosed_list = self._parse_args_core(s)
        except UnquotedCharError as e:
            if s[e.i] != ']':
                raise UnquotedCharError(s, e.i, e.parsed_args)
            
            return s[e.i + 1:].rstrip(), e.parsed_args
        else:
            raise UnclosedListError(unclosed_list, s)
        

    def parse_kwargs(self, s: str) -> TKwargs:
        s = self.pre(s)

        kwargs: dict[TKwargK, TKwargV] = {}
        
        while s:
            s, k = self._parse_kw_name(s)
            s, v = self._parse_kw_value(s)

            k, v = self.post_kwarg((k, v))

            if k in kwargs:
                raise KeywordNotUniqueError(k, (kwargs[k], v))
            
            kwargs[k] = v

            s = s.lstrip()

        return self.post_kwargs(kwargs)
            

def __main() -> None:
    parser = ArgParser(lambda arg: arg, lambda args: args, lambda kwarg: kwarg, lambda kwargs: kwargs)

    while True:
        try:
            result = parser.parse_kwargs(input("Input: "))
        except ValueError as e:
            print("Error Class:", e.__class__.__name__, "args:", e.args)
        else:
            print("Result:", result)

if __name__ == '__main__':
    __main()