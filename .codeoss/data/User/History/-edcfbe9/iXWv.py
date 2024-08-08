# main.py
from contextlib import asynccontextmanager
from typing import Union, Optional, Annotated, Dict
from app import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from fastapi import FastAPI, Depends
from typing import AsyncGenerator
import asyncio
import json
from sqlalchemy import Column, JSON

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    custorder: Dict[str, str] = Field(sa_column=Column(JSON), default={})
    # custorder: str = Field(index=True)

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True)
    qty: int = Field(default=None, index=True)
    product: Dict[int, str] = Field(sa_column=Column(JSON), default={})



connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)



engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)



def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)


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
            "url": "http://localhost:8003", # ADD NGROK URL Here Before Creating GPT Action
            "description": "Development Server"
        }
        ])

def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "Payment container is running"}


@app.get("/payments/", response_model=list[Payment])
def read_payments(session: Annotated[Session, Depends(get_session)]):
        payments = session.exec(select(Payment)).all()
        return payments


@app.get("/orders/", response_model=list[Order])
def read_orders(session: Annotated[Session, Depends(get_session)]):
        orders = session.exec(select(Order)).all()
        return orders

# , response_model=Order

@app.post("/payment/{order_id}")
def create_payment(payment: Payment, session: Annotated[Session, Depends(get_session)], order_id: int):
        selectedorder = session.exec(select(Order).where(Order.id == order_id)).first()
        print(type(selectedorder.dict()))
        print(selectedorder.dict())
        print(type(payment.custorder))
        payment.custorder.update(selectedorder.dict())
        # payment.custorder = "test abc"
        # session.add(payment)
        # session.commit()
        # session.refresh(payment)
        return payment.email
        try:
        # Set up the MIME message
            msg = MIMEMultipart()
            msg['From'] = "shahnawaz.nazimali@gmail.com"
            msg['To'] = payment.email
            msg['Subject'] = "Payment Successful"
            msg.attach(MIMEText(payment, 'plain'))

        # Send the email via SMTP
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()  # Secure the connection
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, msg.as_string())
                print(f"Email sent to {to_email}")
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to send email")