from typing_extensions import TypedDict

from langgraph.graph import (
    StateGraph,
    START,
    END,
)


class DemoState(TypedDict):
    text: str
    count: int


def add_hello(state: DemoState):
    print(
        "进入 add_hello：",
        state,
    )

    return {
        "text": state["text"] + "你好，",
        "count": state["count"] + 1,
    }


def add_again(state: DemoState):
    print(
        "进入 add_again：",
        state,
    )

    return {
        "text": state["text"] + "再执行一次！",
        "count": state["count"] + 1,
    }


def decide_next(state: DemoState):
    print(
        "开始判断下一步：",
        state,
    )

    if state["count"] < 2:
        return "again"

    return "end"


builder = StateGraph(DemoState)


builder.add_node(
    "add_hello",
    add_hello,
)

builder.add_node(
    "add_again",
    add_again,
)


builder.add_edge(
    START,
    "add_hello",
)


builder.add_conditional_edges(
    "add_hello",
    decide_next,
    {
        "again": "add_again",
        "end": END,
    },
)


builder.add_edge(
    "add_again",
    END,
)


graph = builder.compile()


result = graph.invoke(
    {
        "text": "",
        "count": 0,
    }
)


print(
    "最终 State：",
    result,
)