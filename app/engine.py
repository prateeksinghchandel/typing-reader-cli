from enum import Enum

class CharState(Enum):
    CORRECT = 1
    INCORRECT = 2

class TypingEngine:

    def __init__(self,target):
        self.target=target
        self.cursor=0
        self.correct=0
        self.incorrect=0
        self.states: dict[int, CharState] = {}

    def process_key(self,ch: str) -> None:
        if self.finished():
            return None
        
        expected= self.target[self.cursor]

        if ch==expected:
            self.correct+=1
            self.states[self.cursor]=CharState.CORRECT
        else:
            self.incorrect+=1
            self.states[self.cursor]=CharState.INCORRECT
        self.cursor+=1

    def backspace(self):
        if self.cursor != 0:
            self.cursor-=1
            state = self.states.pop(self.cursor, None)
            if state == CharState.CORRECT:
                self.correct-=1
            elif state == CharState.INCORRECT:
                self.incorrect-=1   
        
    def get_accuracy(self) -> float:
        total=self.correct+self.incorrect
        if total==0:
            return 0.0
        return (self.correct/total)*100

    def finished(self) -> bool:
        return self.cursor>=len(self.target)

    def current_character(self) -> str |None:
        if self.finished():
            return None
        return self.target[self.cursor]

    def current_index(self) -> int:
        return self.cursor

    def get_state(self, index:int) -> CharState | None:
        return self.states.get(index)
