from enum import Enum 

class CharState(Enum):
    # UNTOUCHED = 1
    CORRECT = 1
    INCORRECT = 2

class TypingEngine:

    def __init__(self,target):
        self.target=target
        self.cursor=0
        self.correct=0
        self.incorrect=0
        self.states: list[CharState] = []

    def process_key(self,ch: str) -> None:
        if self.finished():
            return None
        
        expected= self.target[self.cursor]

        if ch==expected:
            self.correct+=1
            self.states.append(CharState.CORRECT)
        else:
            self.incorrect+=1
            self.states.append(CharState.INCORRECT)
        self.cursor+=1

    def backspace(self):
        if self.cursor != 0:
            temp=self.states.pop()
            self.cursor-=1
            if temp == CharState.CORRECT:
                self.correct-=1
            elif temp == CharState.INCORRECT:
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
        if index < 0 or index >= len(self.states):
            return None
        return self.states[index]
    