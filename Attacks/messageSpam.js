s="x";for(;s.length<2048;s+=s);setInterval(()=>{document.querySelector("#message").value = s;sendMessage();},0);
