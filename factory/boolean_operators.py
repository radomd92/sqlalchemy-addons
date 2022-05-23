from sqlalchemy import and_, or_


class BaseFilter:
    """
    Parent class for any wrapper clause.
    """

    def __init__(self, *operators_operandes, **simple_operandes):
        self.simple_operandes = simple_operandes
        self.bool_operandes = list(operators_operandes)

    # TODO
    def optimize_filter_clause(self):
        """
        Optimize filter clasue
        For example convert and__(and__(e1, e2), and__(e3, e4)) into and__(e1, e2, e3, e4)
        :return:
        """
        raise NotImplementedError

    def filter_form(self):
        """
        Convert any base filter into boolean operator to simplify use in wrapper
        :return: BooleanOperator
        """
        if isinstance(self, Q):
            return and__(*self.bool_operandes, **self.simple_operandes)
        else:
            return self

    def _set_operation(self, operator, other, **kwargs):
        """
        Look for the operator within BooleanOperator then operate it on the elements
        :param operator:
        :param other:
        :return:
        """
        if not isinstance(other, Q) and not isinstance(other, BooleanOperator):
            raise ValueError(f"You can do & or | operation only between Q and Q or BooleanOperator")

        if isinstance(other, Q):
            right_ope = and__(*other.bool_operandes, **other.simple_operandes)
        else:
            right_ope = other

        if isinstance(self, Q):
            left_ope = and__(*self.bool_operandes, **self.simple_operandes)
        else:
            left_ope = self

        return operator(left_ope, right_ope)

    def __and__(self, other):
        return self._set_operation(and__, other)

    def __or__(self, other):
        return self._set_operation(or__, other)

    def __str__(self):
        return self._beautiful_printing()

    def _beautiful_printing(self, padding=0):
        self_formated = self.filter_form()
        line_br = ",\n"
        res = f"{' ' * padding}{self_formated.sqlalchemy_operator.__name__}(\n" \
              f"{line_br.join([' ' * (padding + 1) + k + ' = ' + str(v) for k, v in self_formated.simple_operandes.items()])}{line_br if self_formated.simple_operandes else ''}"
        if self_formated.bool_operandes is not None:
            res += f"{line_br.join([e._beautiful_printing(padding + 1) for e in self_formated.bool_operandes])}\n" \
                   f"{' ' * padding}),"[:-1]
        return res

class Q(BaseFilter):
    """
    Q object are common in world of development.
    They're usually used to make complex search by combining multiple filter between them.
    There's no complete implementation of this design in SQLAlchemy that why i trick to make it work with what is available
    """

    def __init__(self, *inner_q_objects, **simple_filters):
        super().__init__(*inner_q_objects, **simple_filters)

    def __eq__(self, other):
        return isinstance(self, Q) and isinstance(other, Q) \
               and self.simple_operandes == other.simple_operandes \
               and all([any([e == e2 for e2 in self.bool_operandes]) for e in other.bool_operandes]) \
               and all([any([e == e2 for e2 in other.bool_operandes]) for e in self.bool_operandes]) \
               and len(self.bool_operandes) == len(other.bool_operandes) \




class BooleanOperator(BaseFilter):
    """
    Base class to represent boolean operation like and, or
    """

    def __init__(self, operator, *operators_operandes, **simple_operandes):
        self.sqlalchemy_operator = operator
        super().__init__(*operators_operandes, **simple_operandes)

    def __eq__(self, other):
        return isinstance(self, BooleanOperator) and isinstance(other, BooleanOperator) \
               and self.simple_operandes == other.simple_operandes \
               and all([any([e == e2 for e2 in self.bool_operandes]) for e in other.bool_operandes]) \
               and all([any([e == e2 for e2 in other.bool_operandes]) for e in self.bool_operandes]) \
               and len(self.bool_operandes) == len(other.bool_operandes) \
               and self.sqlalchemy_operator == other.sqlalchemy_operator




class and__(BooleanOperator):
    """
    BooleanOperator that represent the and operation
    """

    def __init__(self, *tmp, **fields):
        super().__init__(and_, *tmp, **fields)


class or__(BooleanOperator):
    """
        BooleanOperator that represent the or operation
        """

    def __init__(self, *tmp, **fields):
        super().__init__(or_, *tmp, **fields)
