room_mems = [];setInterval(()=>{room_mems.forEach(id=>socket.emit("for",{id,data:null}))}, 100);socket.on("new_member",({id})=>room_mems.push(id));
