// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/* 
4- Lista de tareas con prioridad 
Implemente un contrato que permita a cada usuario manejar su propia lista de tareas 
(ToDoList). 
Cada tarea debe contener:
 - Un id autoincremental. 
 - Un título (string).
  - Una prioridad (entero entre 1 y 5).
   - Un estado (pendiente, en curso, completada).
    - La fecha/hora de creación (timestamp). 
El contrato debe permitir: 
- Agregar nuevas tareas.
 - Actualizar título, prioridad y estado de una tarea.
  - Eliminar tareas.
   - Listar todas las tareas de un usuario, con posibilidad de filtrar por prioridad o estado.
 - Implementar paginación en la consulta de tareas, recibiendo parámetros 
offset y limit. 
Se deben emitir eventos (TaskAdded, TaskUpdated, TaskDeleted, 
TaskStatusChanged) para reflejar las operaciones sobre las tareas.
*/



contract ToDoList {

    mapping(address => User) users; 
    uint private next_id;


    constructor(){
        next_id = 1;
    }

    struct User{
        uint id;
        address user_address;
        uint next_task_id;
        mapping(uint => Task) tasks; 
        uint[] taskids;
     }

    struct Task{
        uint id;
        string title;
        int priority;
        State state;
        uint256 timestamp;
    }

    enum State{
        Pending,
        InCourse,
        Completed
    }




    event TaskCreated(string title, int indexed priority, int indexed state, uint id, address creator);

    function addTask(string memory title, int priority, int state) public returns (uint){
        //el estado debe ser un numero entre 0 y 2
        checkNumbers(0, 2, state);

        //La prioridad debe ser un numero entre 1 y 5
        checkNumbers(1, 5, priority);

        User storage user = getUser(msg.sender);

        if(user.id == 0){
            user.id = next_id;
            user.user_address = msg.sender;
            user.next_task_id = 1;
            next_id++;
        }


        Task memory new_task = Task(user.next_task_id,title,priority,State(state),block.timestamp);


        user.tasks[user.next_task_id] = new_task;
        user.taskids.push(user.next_task_id);
        

        emit TaskCreated(title,priority,state,user.next_task_id,msg.sender);


        user.next_task_id ++;


        return user.next_task_id - 1;
        
    }


    //Por eficiencia voy a decidir hacer 3 funciones diferentes para cada Update
    //Ya que sino deberia hacer varios ifs y valores centinela,
    //no es muy adecuado para un contrato que va a gastar gas
    //Por lo tanto tambien voy a hacer 3 eventos diferentes uno para cada situacion

    event TaskUpdated (address indexed user_address,string old_title, string new_title, int indexed old_priority, int indexed new_priority, uint id);

    function updateTaskTitle(string memory title, uint id) public taskExists(id) {
        require(bytes(title).length > 0, "title cannot be empty");
        User storage user = getUser(msg.sender);
        Task storage task_to_update = getTask(id, user);
        string memory old_title = task_to_update.title;
        int old_priority = task_to_update.priority;
        task_to_update.title = title;
        emit TaskUpdated(msg.sender,old_title, title, old_priority,task_to_update.priority,task_to_update.id);
    }   


    function updateTaskPriority(int priority, uint id) public  taskExists(id) {
        checkNumbers(1, 5, priority);
        User storage user = getUser(msg.sender);
        Task storage task_to_update = getTask(id, user);
        string memory old_title = task_to_update.title;
        int old_priority = task_to_update.priority;
        task_to_update.priority = priority;
        emit TaskUpdated(msg.sender,old_title ,task_to_update.title, old_priority ,priority,task_to_update.id);
    } 

    event TaskStatusChanged (address indexed user_address, State indexed old_state,int indexed new_state, uint id);  

    function updateTaskState(int state, uint id) public  taskExists(id) {
        checkNumbers(0, 2, state);
        User storage user = getUser(msg.sender);
        Task storage task_to_update = getTask(id, user);
        State old_state = task_to_update.state;
        task_to_update.state = State(state);
        emit TaskStatusChanged(msg.sender,old_state, state, task_to_update.id);
    }   


    event TaskDeleted(address indexed user_address, uint indexed id);

    function deleteTask(uint id) public  taskExists(id){
        address user_address = msg.sender;
        User storage user = getUser(user_address);
        //Llamo a getTask porque revierte si no existe
        getTask(id, user);
        delete user.tasks[id];
        delete_task_id(id, user);
        emit TaskDeleted(msg.sender, id);
    }

    function delete_task_id(uint id, User storage user) private {
        uint[] storage a = user.taskids;
        for(uint i = 0; i < user.taskids.length; i++ ){
            if(user.taskids[i] == id){
                a[i] = a[a.length - 1]; // swap con el último
                a.pop();
                return ; //retorno para no seguir gastando gas
            }
        }
        revert("taskid not found");
    }




    function show_user_tasks(
        int priority,
        int state,
        uint offset,
        uint limit
        ) public view returns (Task[]  memory out){

        require(limit > 0, "limit must be > 0");
        address user_address = msg.sender;
        //tiene q ser un numero entre -1 y 2 porque -1 es el indicador de que no se usa filtro ( -1 y 0 para priority por comodidad)
        //y los del enum son 0,1,2
        checkNumbers(-1, 2, state);
        checkNumbers(-1, 5, priority);

        User storage user = getUser(user_address);
        require(user.id != 0, "user not registered");
        uint n = user.taskids.length;

        Task[] memory buf = new Task[](limit);
        uint filled = 0;
        uint skipped = 0;

        for (uint i = 0; i < n && filled < limit; i++) {
            uint id = user.taskids[i];
            Task storage t = user.tasks[id];

            bool matchPriority = (priority == -1 || priority == 0 || t.priority == priority);
            bool matchState    = (state == -1 || t.state == State(state));

            if (matchPriority && matchState) {
                if (skipped < offset) {
                    skipped++;
                } else {
                    buf[filled] = t;
                    filled++;
                }
            }
        }

        if (filled == limit){
            return buf;
        } else {
            out = new Task[](filled);
            for (uint j=0; j<filled;j++){
                out[j] = buf[j];
            }
            return out;
        }
    }

    function show_user_tasks_state_filter(User storage user, int state, Task[] memory out) private view  returns (Task[] memory){
        for(uint i=0; i<user.taskids.length; i++){
            uint id = user.taskids[i];
            if(State(state) == user.tasks[id].state){
                out[i] = user.tasks[id];
            }
        }
        return out;
    }


    function show_user_tasks_priority_filter(User storage user, int priority, Task[] memory out) private view  returns (Task[] memory){
        for(uint i=0; i<user.taskids.length; i++){
            uint id = user.taskids[i];
            if(priority == user.tasks[id].priority){
                out[i] = user.tasks[id];
            }
        }
        return out;
    }


    modifier taskExists(uint id) {
        require(users[msg.sender].tasks[id].id != 0, "task not found");
        _;
    }



    function getTask(uint id, User storage user) private taskExists(id) view returns (Task storage){
        return user.tasks[id];
    }


    function getUser(address user_address) private view returns (User storage){
        return users[user_address];
    }



    function checkNumbers(int number1, int number2, int parameter) private pure {
        require(parameter >= number1 && parameter <= number2, "the value of the parameter is not a valid number");
    }






}