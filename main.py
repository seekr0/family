import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI()

JSON_FILE = "familie.json"

# --- DATEN MODELLE (Was kommt von der App?) ---

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    is_parent: bool  # True = Eltern, False = Kind

class NewTask(BaseModel):
    title: str
    for_user: str    # Für wen ist die Aufgabe?
    created_by: str  # Wer hat sie erstellt? (Muss Elternteil sein)

class TaskDone(BaseModel):
    task_id: int

class DeleteTask(BaseModel):
    task_id: int

# --- HILFSFUNKTIONEN FÜR JSON ---

def load_data():
    if not os.path.exists(JSON_FILE):
        # Wenn Datei nicht existiert, leere Struktur erstellen
        return {"users": [], "tasks": []}
    with open(JSON_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- API ENDPOINTS ---

@app.post("/register")
def register(user: UserRegister):
    data = load_data()
    
    # Prüfen, ob Name schon existiert
    for u in data["users"]:
        if u["username"] == user.username:
            raise HTTPException(status_code=400, detail="Name schon vergeben!")
    
    # User speichern
    new_user = user.dict()
    data["users"].append(new_user)
    save_data(data)
    return {"message": "User erstellt!", "user": new_user}

@app.post("/login")
def login(user: UserLogin):
    data = load_data()
    
    for u in data["users"]:
        if u["username"] == user.username and u["password"] == user.password:
            # Login erfolgreich -> Wir geben zurück, ob es Eltern sind
            return {"status": "success", "is_parent": u["is_parent"], "username": u["username"]}
            
    raise HTTPException(status_code=401, detail="Falscher Name oder Passwort")

@app.post("/add_task")
def add_task(task: NewTask):
    data = load_data()
    
    # 1. Sicherheits-Check: Ist der Ersteller ein Elternteil?
    creator = next((u for u in data["users"] if u["username"] == task.created_by), None)
    
    if not creator or not creator["is_parent"]:
        raise HTTPException(status_code=403, detail="Nur Eltern dürfen Aufgaben erstellen!")
    
    # 2. Aufgabe speichern
    new_task_entry = {
        "id": random.randint(1000, 9999), # Zufällige ID
        "title": task.title,
        "for_user": task.for_user,
        "done": False
    }
    
    data["tasks"].append(new_task_entry)
    save_data(data)
    return {"message": "Aufgabe hinzugefügt", "task": new_task_entry}

@app.get("/tasks/{username}")
def get_tasks(username: str):
    data = load_data()
    # Filtere Aufgaben: Entweder Aufgaben für MICH oder ALLE (wenn ich Eltern bin)
    
    user = next((u for u in data["users"] if u["username"] == username), None)
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    my_tasks = []
    if user["is_parent"]:
        # Eltern sehen alle Aufgaben
        my_tasks = data["tasks"]
    else:
        # Kinder sehen nur ihre eigenen Aufgaben
        my_tasks = [t for t in data["tasks"] if t["for_user"] == username]
        
    return my_tasks

@app.post("/complete_task")
def complete_task(payload: TaskDone):
    data = load_data()
    
    for task in data["tasks"]:
        if task["id"] == payload.task_id:
            task["done"] = True
            save_data(data)
            return {"message": "Super gemacht!", "task": task}

@app.delete("/delete_task")
def delete_task(task: DeleteTask):
    data = load_data()
    
    for i, t in enumerate(data["tasks"]):
        if t["id"] == task.task_id:
            # Nur erledigte Aufgaben können gelöscht werden
            if t["done"]:
                deleted_task = data["tasks"].pop(i)
                save_data(data)
                return {"message": "Aufgabe gelöscht", "task": deleted_task}
            else:
                raise HTTPException(status_code=400, detail="Nur erledigte Aufgaben können gelöscht werden!")
    
    raise HTTPException(status_code=404, detail="Aufgabe nicht gefunden")

@app.get("/users")
def get_users():
    data = load_data()
    # Gibt eine Liste aller Usernamen zurück
    return [{"username": u["username"]} for u in data["users"]]