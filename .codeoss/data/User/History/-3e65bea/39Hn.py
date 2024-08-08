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

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)
    qty: int = Field(default=None, index=True)
    product: Dict[int, str] = Field(sa_column=Column(JSON), default={})

class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)

class Purchase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)
    qty: int = Field(default=None, index=True)
    product: Dict[int, str] = Field(sa_column=Column(JSON), default={})

    


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
    # loop.run_until_complete(consume_messages('orders', 'broker:19092'))
    # task = asyncio.create_task(consume_messages('orders', 'broker:19092'))
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan, title="Hello World API with DB", 
    version="0.0.1",
    servers=[
        {
            "url": "http://localhost:8001", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        ])

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "Orders container is running"}

# Kafka Producer as a dependency
# async def get_kafka_producer():
#     producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
#     await producer.start()
#     try:
#         yield producer
#     finally:
#         await producer.stop()

# @app.post("/orders/", response_model=Order)
# async def create_order(order: Order, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->Order:
#         order_dict = {field: getattr(order, field) for field in order.dict()}
#         order_json = json.dumps(order_dict).encode("utf-8")
#         print("orderJSON:", order_json)
#         # Produce message
#         await producer.send_and_wait("orders", order_json)
#         # session.add(order)
#         # session.commit()
#         # session.refresh(order)
#         return order


@app.get("/orders/", response_model=list[Order])
def read_orders(session: Annotated[Session, Depends(get_session)]):
        orders = session.exec(select(Order)).all()
        return orders

@app.get("/products/{product_id}", response_model=list[Product])
def read_productbyid(session: Annotated[Session, Depends(get_session)], product_id: int):
        productbyid = session.exec(select(Product).where(Product.id == product_id))
        return productbyid



@app.post("/orders/", response_model=Order)
def create_order(order: Order, session: Annotated[Session, Depends(get_session)]):
        # product = read_productbyid(product_id)
        session.add(order)
        # session.add(product)
        session.commit()
        session.refresh(order)
        return order
# , response_model=Order
@app.post("/orders/{product_id}")
def create_order(order: Order, session: Annotated[Session, Depends(get_session)], product_id: int):
    # fetching product
        product = session.exec(select(Product).where(Product.id == product_id)).first()
    # fetching purchases of product
        purchases = session.exec(select(Purchase)).all()
        p = []
        for i in purchases:
            for j, k in i.product.items():
                if (k == product_id):
                    # print("test strings are: ", j, k)
                    # print(i)
                    p.append(i)

    # fetching salesorder of product
        sales = session.exec(select(Order)).all()
        s = []
        for i in sales:
            for j, k in i.product.items():
                if (k == product_id):
                    # print("test strings are: ", j, k)
                    # print(i)
                    s.append(i)
    # fetching quantity of purchased product
        sumpqty = 0
        pname = ""
        for q in p:
            print("The qty of ", q.product["content"], "is", q.qty)
            sumpqty += q.qty
            pname = q.product["content"]

    # fetching quantity of sold product
        sumoqty = 0
        oname = ""
        for q in s:
            print("The qty of ", q.product["content"], "is", q.qty)
            sumoqty += q.qty
            oname = q.product["content"]

        
        stockqty = sumpqty - sumoqty

    # if order quantity is not available, give error or process order
        if order.qty > stockqty:
            return {f"Insuficient order quantity of {pname}. Available Qty is {stockqty}"}
        else:
            order.product.update(product.dict())
            session.add(order)
            session.commit()
            session.refresh(order)
            return order




@app.put("/orders/{order_id}", response_model=Order)
def update_order_by_id(order: Order, order_id: int, product_id: int, session: Annotated[Session, Depends(get_session)]):
    orderbyid = session.exec(select(Order).where(Order.id == order_id))
    product = session.exec(select(Product).where(Product.id == product_id)).first()
    for item in orderbyid:
        item.id = order.id
        item.content = order.content
        item.product = order.product
        # item.product.update(product.dict())
        session.add(item)
        session.commit()
        #session.refresh(orderbyid)
    return orderbyid

@app.get("/orders/{order_id}", response_model=list[Order])
def read_orderbyid(session: Annotated[Session, Depends(get_session)], order_id: int):
        orderbyid = session.exec(select(Order).where(Order.id == order_id))
        return orderbyid


@app.delete("/orders/{order_id}", response_model=list[Order])
def delete_order(session: Annotated[Session, Depends(get_session)], order_id: int):
    orderfordel = session.exec(select(Order).where(Order.id == order_id))
    for item in orderfordel:
        session.delete(item)
    session.commit()
    ordersafterdel = session.exec(select(Order)).all()
    return ordersafterdel

@app.post("/payment/{order_id}", response_model=Payment)
def create_payment(payment: Payment, session: Annotated[Session, Depends(get_session)], order_id: int):
        product = session.exec(select(Product).where(Product.id == product_id)).first()
        print(product)
        purchase.product.update(product.dict())
        session.add(purchase)
        session.commit()
        session.refresh(purchase)
        return purchase