# main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated, Dict
from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from fastapi import FastAPI, Depends
from typing import AsyncGenerator
# from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
import json
from sqlalchemy import Column, JSON

class Purchase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)
    qty: int = Field(default=None, index=True)
    product: Dict[int, str] = Field(sa_column=Column(JSON), default={})

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
    # loop.run_until_complete(consume_messages('purchases', 'broker:19092'))
    # task = asyncio.create_task(consume_messages('purchases', 'broker:19092'))
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    version="0.0.1",
    servers=[
        {
            "url": "http://localhost:8002", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        ])

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "Inventory container is running"}

# Kafka Producer as a dependency
# async def get_kafka_producer():
#     producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
#     await producer.start()
#     try:
#         yield producer
#     finally:
#         await producer.stop()

# @app.post("/purchases/", response_model=Purchase)
# async def create_purchase(purchase: Purchase, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->Purchase:
#         purchase_dict = {field: getattr(purchase, field) for field in purchase.dict()}
#         purchase_json = json.dumps(purchase_dict).encode("utf-8")
#         print("purchaseJSON:", purchase_json)
#         # Produce message
#         await producer.send_and_wait("purchases", purchase_json)
#         # session.add(purchase)
#         # session.commit()
#         # session.refresh(purchase)
#         return purchase


@app.get("/purchases/", response_model=list[Purchase])
def read_purchases(session: Annotated[Session, Depends(get_session)]):
        purchases = session.exec(select(Purchase)).all()
        return purchases

@app.get("/purchases/{product_id}", response_model=list[Purchase])
def read_purchases_by_productid(session: Annotated[Session, Depends(get_session)], product_id: int):
        purchases = session.exec(select(Purchase)).all()
        p = []
        for i in purchases:
            for j, k in i.product.items():
                if (k == product_id):
                    # print("test strings are: ", j, k)
                    # print(i)
                    p.append(i)
        
        return p


# @app.get("/purchases/", response_model=list[Purchase])
# def read_purchases_sumofqty_by_productid(session: Annotated[Session, Depends(get_session)], product_id: int):
#         purchases = session.exec(select(Purchase)).all()
#         p = []
#         for i in purchases:
#             for j, k in i.product.items():
#                 if (k == product_id):
#                     # print("test strings are: ", j, k)
#                     # print(i)
#                     p.append(i)
#         print(p)
#         print(type(p))

#         for q in p:
#             print(q.qty)

        

        # below worked for conversion in dict and fetching qty
        # https://builtin.com/software-engineering-perspectives/convert-list-to-dictionary-python
        # d1=dict(enumerate(p))
        # print(d1[0].qty)
        # print(type(d1[0]))

        # return(p)
        # print(type(p))



@app.get("/products/{product_id}", response_model=list[Product])
def read_productbyid(session: Annotated[Session, Depends(get_session)], product_id: int):
        productbyid = session.exec(select(Product).where(Product.id == product_id))
        return productbyid


@app.post("/purchases/", response_model=Purchase)
def create_purchase(purchase: Purchase, session: Annotated[Session, Depends(get_session)]):
        session.add(purchase)
        session.commit()
        session.refresh(purchase)
        return purchase

@app.post("/purchases/{product_id}", response_model=Purchase)
def create_purchase(purchase: Purchase, session: Annotated[Session, Depends(get_session)], product_id: int):
        product = session.exec(select(Product).where(Product.id == product_id)).first()
        print(product)
        purchase.product.update(product.dict())
        session.add(purchase)
        session.commit()
        session.refresh(purchase)
        return purchase

@app.put("/purchases/{purchase_id}", response_model=Purchase)
def update_purchase_by_id(purchase: Purchase, purchase_id: int, session: Annotated[Session, Depends(get_session)]):
    purchasebyid = session.exec(select(Purchase).where(Purchase.id == purchase_id))
    for item in purchasebyid:
        item.id = purchase.id
        item.content = purchase.content
        session.add(item)
        session.commit()
        #session.refresh(purchasebyid)
    return purchase

@app.get("/purchases/{purchase_id}", response_model=list[Purchase])
def read_purchasebyid(session: Annotated[Session, Depends(get_session)], purchase_id: int):
        purchasebyid = session.exec(select(Purchase).where(Purchase.id == purchase_id))
        return purchasebyid


@app.delete("/purchases/{purchase_id}", response_model=list[Purchase])
def delete_purchase(session: Annotated[Session, Depends(get_session)], purchase_id: int):
    purchasefordel = session.exec(select(Purchase).where(Purchase.id == purchase_id))
    for item in purchasefordel:
        session.delete(item)
    session.commit()
    purchasesafterdel = session.exec(select(Purchase)).all()
    return purchasesafterdel