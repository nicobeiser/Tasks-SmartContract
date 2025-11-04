import os, json, re
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_utils import keccak
from web3._utils.events import get_event_data




load_dotenv()

RPC_HTTP = os.getenv("RPC_HTTP")
CHAIN_ID = int(os.getenv("CHAIN_ID", "11155111"))
CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv("CONTRACT_ADDRESS"))
ACCOUNT = os.getenv("ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")



w3 = Web3(Web3.HTTPProvider(RPC_HTTP))
account_obj = Account.from_key(PRIVATE_KEY)
ACCOUNT = w3.to_checksum_address(account_obj.address)
assert w3.is_connected(), "No conecta al RPC"
with open("abi.json","r",encoding="utf-8") as f:
    ABI = json.load(f)
c = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)



def _event_sig(eabi):
    return f"{eabi['name']}({','.join(i['type'] for i in eabi['inputs'])})"

EVENTS_BY_TOPIC0 = {
    keccak(text=_event_sig(item)): item
    for item in ABI
    if item.get("type") == "event"
}


def send_tx(tx_func):
    # 1) Tomar el nonce de 'pending' para no chocar con txs en mempool
    nonce = w3.eth.get_transaction_count(ACCOUNT, 'pending')

    # 2) Calcular fees EIP-1559 sensatas
    pending_block = w3.eth.get_block('pending')
    base_fee = pending_block.get('baseFeePerGas', w3.eth.gas_price)
    tip = w3.to_wei(2, 'gwei')              # prioridad “normal”
    max_fee = base_fee * 2 + tip            # colchón suficiente

    tx = tx_func.build_transaction({
        "from": ACCOUNT,
        "nonce": nonce,
        "chainId": CHAIN_ID,
        "maxFeePerGas": int(max_fee),
        "maxPriorityFeePerGas": int(tip),
    })

    gas_est = w3.eth.estimate_gas(tx)
    tx["gas"] = int(gas_est * 12 // 10)      # +20%
    signed = account_obj.sign_transaction(tx)
    txh = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(txh)
    print("TX:", txh.hex(), "| status:", rcpt.status, "| gasUsed:", rcpt.gasUsed)
    if rcpt.status != 1:
        raise RuntimeError("La transacción revirtió (status 0)")
    print_events_from_receipt(rcpt)
    return rcpt



#4- Lista de Tareas con Prioridad 
#Requerimientos: 

#a) Leer: obtener todas las tareas o filtrarlas por prioridad o estado. 

#b) Escribir: agregar, actualizar o eliminar tareas. 

#c) Escuchar eventos de tareas (TaskAdded, TaskUpdated, TaskDeleted, TaskStatusChanged). 

#d) Implementar la consulta paginada con parámetros offset y limit.

from web3.exceptions import ContractLogicError

def expect_revert_call(fn, msg=""):
    try:
        fn.call({"from": ACCOUNT})
        print(f"NO revirtio: {msg}")
    except ContractLogicError as e:
        print(f"Revirtio: {msg} | {e}")



states = {
    "pendiente" : 0,
    "en curso" : 1,
    "completada" : 2,
}

statesInverted = {
    0 : "pendiente",
    1  : "en curso",
    2 : "completada",
}

def print_all_tasks():
     response = c.functions.show_user_tasks(-1,-1,0,10).call({"from" : ACCOUNT})
     for t in response:
        tid, title, prio, state, ts = t
        print(f"id: [{tid}] titulo:{title} | prioridad:={prio} | estado={statesInverted.get(state, f'Unknown({state})')} | ts={ts}")


def delete_all_tasks():
     response = c.functions.show_user_tasks(-1,-1,0,10).call({"from" : ACCOUNT})
     for t in response:
        tid, title, prio, state, ts = t
        print(f"id: [{tid}] titulo:{title} | prioridad:={prio} | estado={statesInverted.get(state, f'Unknown({state})')} | ts={ts}")
        delete_task(tid)



def test_pagination_filters_offset():
     print("testeando estado : pendiente")
     response = c.functions.show_user_tasks(-1,states.get("pendiente"),0,10).call({"from" : ACCOUNT})
     for t in response:
        tid, title, prio, state, ts = t
        print(f"id: [{tid}] titulo:{title} | prioridad:={prio} | estado={statesInverted.get(state, f'Unknown({state})')} | ts={ts}")
     print("testeando prioridad 2")
     response = c.functions.show_user_tasks(2,-1,0,10).call({"from" : ACCOUNT})
     for t in response:
        tid, title, prio, state, ts = t
        print(f"id: [{tid}] titulo:{title} | prioridad:={prio} | estado={statesInverted.get(state, f'Unknown({state})')} | ts={ts}")
     print("testeando offset 1")
     response = c.functions.show_user_tasks(-1,-1,1,10).call({"from" : ACCOUNT})
     for t in response:
        tid, title, prio, state, ts = t
        print(f"id: [{tid}] titulo:{title} | prioridad:={prio} | estado={statesInverted.get(state, f'Unknown({state})')} | ts={ts}")
     print("testeando paginacion 2")
     response = c.functions.show_user_tasks(-1,-1,0,2).call({"from" : ACCOUNT})
     for t in response:
        tid, title, prio, state, ts = t
        print(f"id: [{tid}] titulo:{title} | prioridad:={prio} | estado={statesInverted.get(state, f'Unknown({state})')} | ts={ts}")


def add_task(title, priority, state):
    send_tx(c.functions.addTask(title,priority,state))


def test_add_task():
    add_task("ir a comprar pan",2,states.get("pendiente"))
    #agrego mas de prio 2 y pendiente para testear despues los filtros
    add_task("prio 2",2,states.get("pendiente"))
    add_task("prio 2",2,states.get("completada"))
    add_task("ir a comprar leche",3,states.get("en curso"))
    add_task("ir a jugar al lol",4,states.get("completada"))
    print("Probando Reverts")
    print("--------------------------")
    expect_revert_call(c.functions.addTask("revierte", 6, 0), "priority= 6 fuera de rango")
    expect_revert_call(c.functions.addTask("revierte", 0, 0), "priority= 0 fuera de rango")
    expect_revert_call(c.functions.addTask("revierte", 1, 3), "state= 4 fuera de rango")
    expect_revert_call(c.functions.addTask("revierte", 1, -1), "state = -1 fuera de rango")


def update_task_title(new_title, task_id):
    send_tx(c.functions.updateTaskTitle(new_title,task_id))

def update_task_priority(new_priority, task_id):
    send_tx(c.functions.updateTaskPriority(new_priority,task_id))

def update_task_state(new_state, task_id):
    send_tx(c.functions.updateTaskState(new_state,task_id))


def test_update_task():
    update_task_title("Comprar Leche!", 4)
    update_task_priority(4, 2)
    update_task_state(states.get("en curso"), 3)



def delete_task(task_id):
    send_tx(c.functions.deleteTask(task_id))


def test_delete_task():
    delete_task(5)






def _print_event(ev):
    n = ev["event"]; a = ev["args"]
    if n == "TaskCreated":
        print(f"→ TaskCreated user={a['creator']} id={a['id']} title='{a['title']}' prio={a['priority']} state={statesInverted.get(a['state'])}")
    elif n == "TaskUpdated":
        print(f"→ TaskUpdated id={a['id']} user={a['user_address']} old_title={a['old_title']} new_title='{a['new_title']}' old_priority={a['old_priority']} new_priority={a['new_priority']}")
    elif n == "TaskStatusChanged":
        print(f"→ TaskStatusChanged id= {a['id']}  user={a['user_address']} {statesInverted.get(a['old_state'])} → {statesInverted.get(a['new_state'])}")
    elif n == "TaskDeleted":
        print(f"→ TaskDeleted user={a['user_address']} id={a['id']}")
    else:
        print(f"→ {n} {dict(a)}")

def print_events_from_receipt(rcpt):
    found = False
    if not rcpt or not getattr(rcpt, "logs", None):
        print("Eventos: (ninguno)")
        return

    for log in rcpt.logs:
        if log["address"].lower() != CONTRACT_ADDRESS.lower():
            continue
        abi = EVENTS_BY_TOPIC0.get(log["topics"][0])
        if not abi:
            continue
        try:
            ev = get_event_data(w3.codec, abi, log)
            _print_event(ev)
            found = True
        except Exception as e:
            print("No pude decodificar un evento:", e)

    if not found:
        print("Eventos: (ninguno de este contrato)")








def main():
    print("Conectado:", w3.is_connected())
    print("Contrato:", CONTRACT_ADDRESS)
    print("Sender  :", ACCOUNT)


    #expect_revert_call(c.functions.deleteTask(67676))

  
    #test_add_task()

    #print("-------- ALL TASKS AFTER INSERT --------------")

    #print_all_tasks()

    #test_update_task()

    #print("-------- ALL TASKS AFTER UPDATE --------------")

    #print_all_tasks()

    #test_delete_task()

    #print("-------- ALL TASKS AFTER Delete --------------")

    #print_all_tasks()

    #print("-------- BEFORE TRYING PAGINATION AND OFFSET --------------")

    #test_pagination_filters_offset()

    #delete_all_tasks()




if __name__ == "__main__":
    main()