from collections import deque
from typing import TYPE_CHECKING, ClassVar, Iterable

from textual.binding import Binding
from textual.suggester import Suggester
from textual.widgets import Input


class CustomSuggester(Suggester):
    def __init__(self, suggestions: list[str], case_sensitive: bool = True) -> None:
        super().__init__(use_cache=False, case_sensitive=case_sensitive)
        self._suggestions: deque[str] = deque(suggestions,maxlen=64)
        self._for_comparison: deque[str] = deque(suggestions,maxlen=64)

    async def get_suggestion(self, value: str) -> str | None:
        for idx, suggestion in enumerate(self._for_comparison):
            if suggestion.startswith(value):
                return self._suggestions[idx]
        return None

    def add_suggestion(self, suggestion: str) -> None:
        #if suggestion not in self._suggestions:
        self._suggestions.appendleft(suggestion)
        self._for_comparison.appendleft(
            suggestion if self.case_sensitive else suggestion.casefold()
        )


class CustomInput(Input):
    BINDINGS: ClassVar[list[BindingType]] = Input.BINDINGS
    BINDINGS.extend([
        Binding("up", "cursor_up", "Backward input / suggestion", show=False),
        Binding("down", "cursor_down", "Forward input / suggestion", show=False),                
        
    ])


    def __init__(self,*args,**kwargs) -> None:
        super().__init__(*args,**kwargs)
        self.backward_forward_index = None

        
    def action_cursor_right(self) -> None:
        """Accept an auto-completion or move the cursor one position to the right."""
        if self._cursor_at_end and self._suggestion:
            self.value = self._suggestion
            self.cursor_position = len(self.value)
        else:
            self.cursor_position += 1


    def action_cursor_up(self) -> None:
        """Backward in input list."""
        if self.backward_forward_index == None:
            self.backward_forward_index = 0            
        else:
            self.backward_forward_index = (self.backward_forward_index+1) % len(self.suggester._suggestions)
        self.value = self.suggester._suggestions[self.backward_forward_index]
        
    def action_cursor_down(self) -> None:
        """Forward in input list."""
        if self.backward_forward_index == None:
            self.backward_forward_index = len(self.suggester._suggestions)-1
        else:
            self.backward_forward_index = (self.backward_forward_index-1) % len(self.suggester._suggestions)
        self.value = self.suggester._suggestions[self.backward_forward_index]
        

