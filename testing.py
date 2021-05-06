

class BigOne():
    def __init__(self):
        self.bla = 'bla!'

    def hello(self):
        print('hello!')


class SmallOne():
    def check(self, bigOneName):
        bigOneName.hello()


testBig = BigOne()
testSmall = SmallOne()

testSmall.check(testBig)