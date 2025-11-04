# Tasks-SmartContract
My first Solidity smart contract on Sepolia: a per-user To-Do List with priorities (1–5), statuses (Pending/InCourse/Completed), timestamps, CRUD operations, filtering by priority/state, and paginated listing. Emits TaskCreated/TaskUpdated/TaskDeleted/TaskStatusChanged events.


Steps to try this Smart Contract out:
1- Create a .env File at the level of the abi, ejercicio4.py and ejercicio4.sol
2- Fill it with:
RPC_HTTP=https://sepolia.infura.io/v3/Your-Proyect-Id
RPC_WS=wss://sepolia.infura.io/ws/v3/Your-Proyect-Id
CONTRACT_ADDRESS=0x107df51f2ea5ceFa29a3affB12B392E02E5982C9
ACCOUNT_ADDRESS=Your-public-address
PRIVATE_KEY=Your-private-key
CHAIN_ID=11155111
3-Modify test_add_task, test_update_task(), test_delete_task() and test_pagination_filters_offset() as you want
4-Uncomment lines of main()
5-Run ejercicio4.py


NOTE: Task ids start on 1, even after delete they keep incrementing, so if you do a "delete_all_tasks()" and you had 20 tasks, your next task_id is going to be 21.



