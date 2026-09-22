from movie_agent import run_movie_agent
from fastapi import FastAPI, HTTPException, Query, status
from schemas import (
    MovieCreate,
    MovieResponse,
    MoviePageResponse,
    MovieUpdate,
    AIChatRequest,
    AIChatResponse,
    UserMemoryUpdate,
    UserMemoryResponse,
)
from database import (
    init_database,
    get_movie_by_id,
    get_movies_page,
    get_movie_count,
    add_movie,
    update_movie,
    partial_update_movie,
    delete_movie,
    search_movies_db,
    filter_movies_db,
    update_user_memory,
    get_user_memory,
)
app = FastAPI()
init_database()

@app.get("/")
def root():
    return {"message": "电影资料查询系统"}


@app.get("/movies",response_model=MoviePageResponse)
def get_movies(
    page:int =Query(default=1,ge=1),
    page_size:int = Query(default=3,ge=1,le=100),
):
    items=get_movies_page(page=page,page_size=page_size)
    total=get_movie_count()
    return {
        "page":page,
        "page_size":page_size,
        "total":total,
        "items":items
    }

@app.get("/movies/search",response_model=list[MovieResponse])
def search_movies(keyword:str):
    return search_movies_db(keyword)

@app.get("/movies/filter",response_model=list[MovieResponse])
def filter_movies(
    keyword:str | None=None,
    min_score:float | None=Query(default=None,ge=0,le=10),
    year: int |  None=Query(default=None,ge=1888)
):
    return filter_movies_db(
        keyword=keyword,
        min_score=min_score,
        year=year
    )
@app.get("/movies/{movie_id}",response_model=MovieResponse)
def get_movie(movie_id:int) :
    movie=get_movie_by_id(movie_id)
    if movie is None:
        raise HTTPException(status_code=404,detail=f"没有找到ID为{movie_id}的电影")
    return movie



@app.post("/movies",status_code=status.HTTP_201_CREATED,response_model=MovieResponse)
def create_movie(movie:MovieCreate) :
    movie_data={
        "name":movie.name,
        "score":movie.score,
        "year":movie.year,
        "type":movie.type,
        
    }
    movie_id=add_movie(movie_data)
    return{
        "id":movie_id,
        **movie_data
    }

@app.put(
    "/movies/{movie_id}",
    response_model=MovieResponse
)
def update_movie_api(
    movie_id:int,
    movie:MovieCreate
):
    movie_data={
        "name":movie.name,
        "score":movie.score,
        "year":movie.year,
        "type":movie.type,
    }
    updated_movie = update_movie(
        movie_id,
        movie_data
    )


    if updated_movie is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有找到ID为{movie_id}的电影"
        )


    return updated_movie

@app.patch(
    "/movies/{movie_id}",
    response_model=MovieResponse
)
def partial_update_movie_api(
    movie_id:int,
    movie:MovieUpdate
):
    update_data = movie.model_dump(
        exclude_unset=True
    )
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="至少需要提交一个要修改的字段"
        )
    updated_movie = partial_update_movie(
        movie_id,
        update_data
    )
    if updated_movie is None:

        raise HTTPException(
            status_code=404,
            detail=f"没有找到ID为{movie_id}的电影"
        )
    return updated_movie
@app.delete("/movies/{movie_id}")
def delete_movie_api(movie_id:int):
    movie = delete_movie(movie_id)
    if movie is None:
        raise HTTPException(
            status_code=404,
            detail=f"没有找到ID为{movie_id}的电影"
        )
    return {
        "message":f"已删除ID为{movie_id}的电影",
        "deleted_movie":movie,
    }

@app.post(
    "/ai/chat",
    response_model=AIChatResponse,
)
def ai_chat(request: AIChatRequest):
    try:
        answer = run_movie_agent(
            user_input=request.message,
            session_id=request.session_id,
            user_id=request.user_id
        )

        return {
            "session_id": request.session_id,
            "answer": answer,
        }

    except Exception as error:
        print(
            f"Agent运行失败：{error}"
        )

        raise HTTPException(
            status_code=500,
            detail="AI Agent服务暂时不可用",
        )


@app.put(
    "/ai/memory/{user_id}",
    response_model=UserMemoryResponse,
)
def update_memory(
    user_id: str,
    request: UserMemoryUpdate,
):
    memory = update_user_memory(
        user_id=user_id,
        favorite_type=request.favorite_type,
        preferred_min_score=request.preferred_min_score,
    )

    return memory


@app.get(
    "/ai/memory/{user_id}",
    response_model=UserMemoryResponse,
)
def get_memory(user_id: str):
    memory = get_user_memory(user_id)

    if memory is None:
        raise HTTPException(
            status_code=404,
            detail="没有找到该用户的长期记忆",
        )

    return memory