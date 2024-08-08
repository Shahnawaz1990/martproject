# main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated
from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from fastapi import FastAPI, Depends
from typing import AsyncGenerator
# from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
import json

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)


# only needed for psycopg 3 - replace postgresql
# with postgresql+psycopg in settings.DATABASE_URL
connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)


# recycle connections after 5 minutes
# to correspond with the compute scale down
engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

#engine = create_engine(
#    connection_string, connect_args={"sslmode": "require"}, pool_recycle=300
#)


def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)

# async def consume_messages(topic, bootstrap_servers):
#     # Create a consumer instance.
#     consumer = AIOKafkaConsumer(
#         topic,
#         bootstrap_servers=bootstrap_servers,
#         group_id="my-group",
#         auto_offset_reset='earliest'
#     )

#     # Start the consumer.
#     await consumer.start()
#     try:
#         # Continuously listen for messages.
#         async for message in consumer:
#             print(f"Received message: {message.value.decode()} on topic {message.topic}")
#             # Here you can add code to process each message.
#             # Example: parse the message, store it in a database, etc.
#     finally:
#         # Ensure to close the consumer when done.
#         await consumer.stop()


# # The first part of the function, before the yield, will
# # be executed before the application starts.
# # https://fastapi.tiangolo.com/advanced/events/#lifespan-function
# # loop = asyncio.get_event_loop()
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
    # loop.run_until_complete(consume_messages('products', 'broker:19092'))
    # task = asyncio.create_task(consume_messages('products', 'broker:19092'))
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    version="0.0.1",
    servers=[
        {
            "url": "http://localhost:8000", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        ])

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "Panacloud updated again on sixteen july outside"}

# Kafka Producer as a dependency
# async def get_kafka_producer():
#     producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
#     await producer.start()
#     try:
#         yield producer
#     finally:
#         await producer.stop()

# @app.post("/products/", response_model=Product)
# async def create_product(product: Product, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->Product:
#         product_dict = {field: getattr(product, field) for field in product.dict()}
#         product_json = json.dumps(product_dict).encode("utf-8")
#         print("productJSON:", product_json)
#         # Produce message
#         await producer.send_and_wait("products", product_json)
#         # session.add(product)
#         # session.commit()
#         # session.refresh(product)
#         return product


@app.get("/products/", response_model=list[Product])
def read_products(session: Annotated[Session, Depends(get_session)]):
        products = session.exec(select(Product)).all()
        return products

@app.post("/products/", response_model=Product)
def create_product(product: Product, session: Annotated[Session, Depends(get_session)]):
        session.add(product)
        session.commit()
        session.refresh(product)
        return product


@app.get("/products/", response_model=list[Product])
def read_products(session: Annotated[Session, Depends(get_session)]):
        products = session.exec(select(Product)).all()
        return products


@app.put("/products/{product_id}", response_model=Product)
def update_product_by_id(product: Product, product_id: int, session: Annotated[Session, Depends(get_session)]):
    productbyid = session.exec(select(Product).where(Product.id == product_id))
    for item in productbyid:
        item.id = product.id
        item.content = product.content
        session.add(item)
        session.commit()
        #session.refresh(productbyid)
    return product

@app.get("/products/{product_id}", response_model=list[Product])
def read_productbyid(session: Annotated[Session, Depends(get_session)], product_id: int):
        productbyid = session.exec(select(Product).where(Product.id == product_id))
        return productbyid


@app.delete("/products/{product_id}", response_model=list[Product])
def delete_product(session: Annotated[Session, Depends(get_session)], product_id: int):
    productfordel = session.exec(select(Product).where(Product.id == product_id))
    for item in productfordel:
        session.delete(item)
    session.commit()
    productsafterdel = session.exec(select(Product)).all()
    return productsafterdel
