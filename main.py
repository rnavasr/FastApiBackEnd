from fastapi import FastAPI, Request, BackgroundTasks
from fastapi_crudrouter import SQLAlchemyCRUDRouter
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import hmac
import hashlib
import os

from database import engine, Base, SessionLocal
from models import Producto
from schemas import ProductoSchema

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API eCommerce 2025 UTEQ")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD automático para el modelo Producto
router = SQLAlchemyCRUDRouter(
    schema=ProductoSchema,   
    db_model=Producto,       
    db=get_db,               
    prefix="productos"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "API eCommerce 2025"}


# ====== WEBHOOK PARA AUTO-DESPLIEGUE ======
def ejecutar_deploy():
    """Ejecuta el script de despliegue en segundo plano"""
    try:
        subprocess.Popen(["/opt/bitnami/projects/backendFastAPI/deploy.sh"])
    except Exception as e:
        print(f"Error al ejecutar deploy: {e}")


@app.post("/webhook")
async def webhook_github(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint que recibe webhooks de GitHub.
    Cuando detecta un push a main, ejecuta el despliegue automático.
    """
    try:
        payload = await request.json()
        
        # Verificar que es un push al branch main
        if payload.get("ref") == "refs/heads/main":
            # Ejecutar despliegue en segundo plano
            background_tasks.add_task(ejecutar_deploy)
            
            return {
                "status": "success", 
                "message": "Despliegue automático iniciado",
                "branch": "main"
            }
        
        return {
            "status": "ignored", 
            "message": f"Push a {payload.get('ref')}, solo se despliega main"
        }
    
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e)
        }


@app.get("/deploy-status")
def deploy_status():
    """Endpoint para ver el estado de los últimos despliegues"""
    try:
        with open("/opt/bitnami/projects/backendFastAPI/deploy.log", "r") as f:
            ultimas_lineas = f.readlines()[-30:]  # Últimas 30 líneas
            return {
                "status": "success",
                "log": "".join(ultimas_lineas)
            }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "No hay logs de despliegue aún"
        }