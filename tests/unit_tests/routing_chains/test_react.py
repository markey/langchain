"""Unit tests for ReAct."""

from typing import Any, List, Mapping, Optional, Union

import pytest

from langchain.docstore.base import Docstore
from langchain.docstore.document import Document
from langchain.llms.base import LLM
from langchain.prompts.prompt import PromptTemplate
from langchain.routing_chains.react.base import ReActChain, ReActRouterChain

_PAGE_CONTENT = """This is a page about LangChain.

It is a really cool framework.

What isn't there to love about langchain?

Made in 2022."""

_FAKE_PROMPT = PromptTemplate(input_variables=["input"], template="{input}")


class FakeListLLM(LLM):
    """Fake LLM for testing that outputs elements of a list."""

    def __init__(self, responses: List[str]):
        """Initialize with list of responses."""
        self.responses = responses
        self.i = -1

    def __call__(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        """Increment counter, and then return response in that index."""
        self.i += 1
        return self.responses[self.i]

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        return {}


class FakeDocstore(Docstore):
    """Fake docstore for testing purposes."""

    def search(self, search: str) -> Union[str, Document]:
        """Return the fake document."""
        document = Document(page_content=_PAGE_CONTENT)
        return document


def test_predict_until_observation_normal() -> None:
    """Test predict_until_observation when observation is made normally."""
    outputs = ["foo\nAction 1: search[foo]"]
    fake_llm = FakeListLLM(outputs)
    router_chain = ReActRouterChain(llm=fake_llm)
    output = router_chain.route("")
    assert output.log == outputs[0]
    assert output.tool == "search"
    assert output.tool_input == "foo"


def test_predict_until_observation_repeat() -> None:
    """Test when no action is generated initially."""
    outputs = ["foo", " search[foo]"]
    fake_llm = FakeListLLM(outputs)
    router_chain = ReActRouterChain(llm=fake_llm)
    output = router_chain.route("")
    assert output.log == "foo\nAction 1: search[foo]"
    assert output.tool == "search"
    assert output.tool_input == "foo"


def test_react_chain() -> None:
    """Test react chain."""
    responses = [
        "I should probably search\nAction 1: Search[langchain]",
        "I should probably lookup\nAction 2: Lookup[made]",
        "Ah okay now I know the answer\nAction 3: Finish[2022]",
    ]
    fake_llm = FakeListLLM(responses)
    react_chain = ReActChain(llm=fake_llm, docstore=FakeDocstore())
    inputs = {"question": "when was langchain made"}
    output = react_chain(inputs)
    assert output["answer"] == "2022"


def test_react_chain_bad_action() -> None:
    """Test react chain when bad action given."""
    responses = [
        "I should probably search\nAction 1: BadAction[langchain]",
    ]
    fake_llm = FakeListLLM(responses)
    react_chain = ReActChain(llm=fake_llm, docstore=FakeDocstore())
    with pytest.raises(ValueError):
        react_chain.run("when was langchain made")