class NumberFormatter:

    @staticmethod
    def format(num):
        num = str(num)
        p1 = num[0:2]
        p2 = num[2:6]
        p3 = num[6:11]
        num_f = f'({p1}) {p2}-{p3}'
        return num_f