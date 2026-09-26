from mcp.server import MCPServer

from database import (
    get_movie_by_id,
    search_movies_db,
    filter_movies_db,
)


mcp = MCPServer("Movie MCP Server")

@mcp.tool()
def get_movie(movie_id: int):
    """根据电影 ID 查询电影。"""
    return get_movie_by_id(movie_id)


@mcp.tool()
def search_movies(keyword: str):
    """根据关键词搜索电影。"""
    return search_movies_db(keyword)


@mcp.tool()
def filter_movies(
    keyword: str | None = None,
    min_score: float | None = None,
    year: int | None = None,
):
    """根据类型、评分和年份筛选电影。"""

    return filter_movies_db(
        keyword=keyword,
        min_score=min_score,
        year=year,
    )


if __name__ == "__main__":
    mcp.run()