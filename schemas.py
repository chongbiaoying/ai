from pydantic import BaseModel, Field


class MovieCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
        description="电影名称",
    )

    score: float = Field(
        ge=0,
        le=10,
        description="电影评分，范围是0到10",
    )

    year: int = Field(
        ge=1888,
        description="电影上映年份",
    )

    type: str = Field(
        min_length=1,
        max_length=20,
        description="电影类型",
    )


class MovieResponse(BaseModel):
    id: int
    name: str
    score: float
    year: int
    type: str


class MoviePageResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[MovieResponse]


class MovieUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="电影名称",
    )

    score: float | None = Field(
        default=None,
        ge=0,
        le=10,
        description="电影评分，范围是0到10",
    )

    year: int | None = Field(
        default=None,
        ge=1888,
        description="电影上映年份",
    )

    type: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="电影类型",
    )