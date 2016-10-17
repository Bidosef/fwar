var socket = new WebSocket("ws://" + window.location.host + "/ws/" + room_id + "/" + pseudo );
var admin_hidden = true;
var counter;


$(document).ready(function(){
    //disable copy paste
    $('#chat').bind("cut copy",function(e) {
        e.preventDefault();
    });

    var need_to_add_pseudo = true;
    $("#player_list li").each(function(){
        if(pseudo == $(this).text())
            need_to_add_pseudo = false;
    });
    if(need_to_add_pseudo)
        $("#spectators").append("<li>"+pseudo+"</li>");


    socket.onopen = function(event){
        $("#chat_button").click(function(){
            send();
        });
        $("#chat_text_input").keyup(function(key){
            if(key.keyCode == 13)
                send();
        });
        setInterval(ping, 30000);
        function ping(){
            socket.send(".");
        }

    }
    socket.onerror  = function(event) {
        console.log("ERROR opening WebSocket.");
        $('body').html("<h1>ERREUR de connection</h1><p>Essayez de recharger la page</p>");
    }
    socket.onclose  = function(event) {
        console.log("close");
        $('body').html("<h1>ERREUR de connection</h1><p>Essayez de recharger la page</p>");
    }


    socket.onmessage = function(event){
        var msg = event.data;
        console.log(msg);
        switch(msg.charAt(0)){
            case 'Q': window.location.href = "/";
            break;
            case 'S': if(msg == "STOP")stop_game();else start(msg.substring(1));
            break;
            case 'G': game(msg.substring(1));
            break;
            case 'A': action(msg.substring(1));
            break;
            case 'T': time_handler(msg.substring(1)); 
            break;
            case 'P': reset_votes();
            break;
            case 'R': add_action(msg.substring(1));
            break;
            case '0': info(msg.substring(1));
            break;
            case '1': add_message(msg.substring(0,2), msg.substring(2));
            break;
            case '2': set_compo(msg.substring(1));
            break;
        }
    }

    //Actions
    $("#join_button").click(function(){
        socket.send("JOIN");
    });
    $("#start_button").click(function(){
        socket.send("20");
    });


    //Menu
    $("#quit").click(function(){
        socket.send("QUIT");
        socket.close();
        window.location.href = "/";
    });


    //ADMIN 
    $(".add").click(function(){add($(this));});
    $(".less").click(function(){less($(this));});
    $("#uniques>div>img").click(function(){select($(this));});
    $("#confirmation_compo").click(function(){
        var compo = "21"+$("#moderateurs").val()+"/"+$("#forumeurs").val()+"/"+$("#multicompte").val()+"/"+$("#aleatoire").val();
        $("#uniques>.simple_block_selected>input").each(function(){
            compo += "/"+$(this).attr("name");
        });
        socket.send(compo);
    });

    $("#edit_compo").click(function(){
        if(admin_hidden){
            $(this).animate({"left":"0px"}, "slow");
            admin_hidden = false;
        }
    });
    $("#close").click(function(event){
        $("#edit_compo").animate({"left":"-400px"}, "slow");
        admin_hidden = true;
        event.stopPropagation();
    });
    $("#edit_compo").animate({"left":"-400px"}, "slow");
});


/************************************************/
/*                                              */
/*             SENDING FUNCTIONS                */
/*                                              */
/************************************************/

function send(){
    var content = $("#chat_text_input").val();
    if(content.charAt(0) == '/'){
        if(content.substring(1,5) == "kick"){
            socket.send("22"+content.substring(6));
            $("#chat_text_input").val("");
            return;
        }else if(content.substring(1,3) == "ip"){
            socket.send("24");
            $("#chat_text_input").val("");
            return;
        }else if(content.substring(1,5) == "info"){
            socket.send("25");
            $("#chat_text_input").val("");
            return;
        }
    }
    if(content!=""){
        socket.send("0"+content);
        $("#chat_text_input").val("");
    }
}


/************************************************/
/*                                              */
/*             ON MESSAGE FUNCTIONS             */
/*                                              */
/************************************************/
function info(msg){
    var info_val = msg.substring(1);
    console.log(msg);
    console.log(info_val);
    switch(msg.charAt(0)){
        case '0': 
            //add_message("i", info_val + " s'est connecté !");
            $("#spectators").append("<li>"+info_val+"</li>");
        break;
        case '1': 
            add_message("i", info_val + " a rejoint la partie.");
            $("#player_list li").each(function(){
                if($(this).text() == info_val){
                    $(this).remove();
                }
            });
            $("#players").append("<li>" + info_val + "</li>");
            $("#votes").append("<li class='" + info_val + "'></li>");
            $("#nb_votes").append("<li class='" + info_val + "'>0</li>");
            if(info_val == pseudo)
                $("#join_button").remove();
        break;
        case '2': 
            //add_message("i", info_val + " s'est deconnecté.");
            $("#player_list li").each(function(){
                if($(this).text() == info_val){
                    $(this).remove();
                }
            });
            $("#player_list ."+info_val).remove();
            if($("#player_list li").first().text() == pseudo)
                window.location.reload(true); 
        break;
        case '3':
            var pseudos = info_val.split(":");
            if(pseudos[1] == ""){
                add_message("i", pseudos[0] + " signale personne.");
                var last_signal = $("#votes ." + pseudos[0]).text().substring(1);
                $("#nb_votes ." + last_signal).text(parseInt($("#nb_votes ." + last_signal).text())-1);
                $("#votes ." + pseudos[0]).text("");
            }else{
                add_message("i", pseudos[0] + " signale " + pseudos[1]+".");
                var last_signal = $("#votes ." + pseudos[0]).text().substring(1);
                if(last_signal != "")
                    $("#nb_votes ." + last_signal).text(parseInt($("#nb_votes ." + last_signal).text())-1);
                $("#votes ." + pseudos[0]).text(">" + pseudos[1]);
                $("#nb_votes ." + pseudos[1]).text(parseInt($("#nb_votes ." + pseudos[1]).text())+1);
            }
        break;
        case '4':
            $("#players li").each(function(){
                if($(this).text() == info_val){
                    $(this).remove();
                }
            });
            $("#dead_players").append("<li>"+info_val+"</li>");
            $("#player_list ."+info_val).remove();
        break;
        case '6':
            var pseudos = info_val.split(":");
            if(pseudos[1] == ""){
                add_message("il", pseudos[0] + " ne veut bannir personne.");
            }else{
                add_message("il", pseudos[0] + " veut bannir " + pseudos[1]+".");
            }
        break;
        case '7': 
            add_message("i", info_val + " a été kick !");
            $("#player_list li").each(function(){
                if($(this).text() == info_val){
                    $(this).remove();
                }
            });
            $("#player_list ."+info_val).remove();
        break;
        case '8': $("#nb_votes ."+info_val).text(parseInt($("#nb_votes ." + info_val).text())+2);
        break;
        case '9': add_message("i","La room a été recréée, cliquez <a href='/room/"+info_val+"'>ici</a> pour la rejoindre !");
        break;
        default: add_message("i", info_val);
    }
}

function reset_votes(){
    $("#nb_votes>li").each(function(){
        $(this).text("0");
    });
    $("#votes>li").each(function(){
        $(this).text("");
    });
}

function add_message(msg_type, msg){
    $("#msg_list").append("<li class=m" + msg_type + ">" + msg + "</li>");
    $("#chat_text").scrollTop($("#chat_text")[0].scrollHeight);
}

/************************************************/
/*                                              */
/*             GAME FUNCTIONS                   */
/*                                              */
/************************************************/

function start(msg){
    if(msg == "E")
        alert("Le jeu ne peut pas encore commencer, il n'y a pas assez de joueurs !");
    else if(msg == "O"){
        $("#msg_list").append("<h1>Le jeu vient de commencer !</h1>");
    }else{
        $("#msg_list").append("<h1>Le jeu vient de commencer !</h1>");
        $("#start_button").remove();
        $("#edit_compo").remove();
        $("#quit").remove();
    }
}
function stop_game(){
    set_time(0);
    stop_time_count();
    $("#menu").append("<button id='quit'>Quitter</button>");
    $("#quit").click(function(){
        socket.send("QUIT");
        socket.close();
        window.location.href = "/";
    });
    if(creator){
        add_message("i","Pour recréer une room, cliquez <a id='recreate' href='/room/redirect'>ici</a> !");
        $("#recreate").click(function(){
            socket.send("23");
        });
    }
}

function game(msg){
    add_message("g",msg);
}
function action(msg){
    add_message("a",msg);
}


function time_handler(msg){
    if(parseInt(msg)!=10)
        $("#action").html("");
    stop_time_count();
    set_time(parseInt(msg));
    start_time_count();
}

function set_time(time){
    var min = (time / 60) >> 0;
    var sec = time % 60;
    if(sec >= 10)
        $("#time>h3").text(min + ":" + sec);
    else
        $("#time>h3").text(min + ":0" + sec);
}

function start_time_count(){
    counter = setInterval(time_count, 1000);
}
function stop_time_count(){
    window.clearInterval(counter);
}
function time_count(){
    var t = $("#time>h3").text().split(":");
    var time = parseInt(t[0])*60+parseInt(t[1])-1;
    set_time(time);
}



function add_action(msg){
    var req = msg.split(":");
    if(req[0] == "S1")
        select1(req.slice(1));
    else if(req[0] == "S2")
        select2(req.slice(1));
    else if(req[0] == "B")
        button(req.slice(1));
}

function select1(args){
    $("#action").append("<select id='S1'></select>");
    for(var i=1; i<args.length; i++){
        $("#S1").append("<option value='"+(i-2)+"'>"+args[i]+"</option>");
    }
    $("#action").append("<button id='S1_button'>"+args[0]+"</button>");
    $("#S1_button").click(function(){
        socket.send("1"+$("#S1 :selected").val());
    });
}

function select2(args){
    $("#action").append("<select id='S2'></select>");
    for(var i=1; i<args.length; i++){
        $("#S2").append("<option value='"+(i-2)+"'>"+args[i]+"</option>");
    }
    $("#action").append("<button id='S2_button'>"+args[0]+"</button>");
    $("#S2_button").click(function(){
        socket.send("1"+$("#S2 :selected").val());
        $("#S2").remove();
        $("#S2_button").remove();
    });
}

function button(args){
    $("#action").append("<p id='B'>" + args[1] + "<button id='B_button'>" + args[0] + "</button>" + "</p>");
    $("#B_button").click(function(){
        socket.send("1");
        $("#B").remove();
    });
}

/************************************************/
/*                                              */
/*             ADMINS FUNCTIONS                 */
/*                                              */
/************************************************/

function less(element){
    var nb = parseInt(element.siblings('input').val());
    if(nb>0)
        element.siblings('input').val(nb-1);
    if(nb == 2 && element.siblings('input').attr("id") == "multicompte")
        element.siblings('input').val(0);
}
function add(element){
    var nb = parseInt(element.siblings('input').val());
    element.siblings('input').val(nb+1);
    if(nb == 0 && element.siblings('input').attr("id") == "multicompte")
        element.siblings('input').val(2);
}
function select(element){
    element.siblings('input').prop("checked", !element.siblings('input').is(":checked"));
    if(element.siblings('input').is(":checked"))
        element.closest('div').toggleClass("simple_block simple_block_selected");
    else
        element.closest('div').toggleClass("simple_block_selected simple_block");
}


function set_compo(string){
    if(string=="E"){
        alert("Erreur ! La composition n'a pas pu être changé. Verifiez qu'il n'y ait pas trop de joueurs déjà présent pour votre nouvelle composition.");
        return;
    }
    var compo = string.split("/");
    $("#compo").html("<ul></ul>");
    $("#compo>ul").append("<li>Moderateur(s) : "+ compo[0] + "</li>");
    $("#compo>ul").append("<li>Forumeur(s) : "+ compo[1] + "</li>");
    $("#compo>ul").append("<li>Multi-comptes : "+ compo[2] + "</li>");
    $("#compo>ul").append("<li>Aléatoires : "+ compo[3] + "</li>");
    for(var i=4; i<compo.length; i++){
        $("#compo>ul").append("<li>" + compo[i] + "</li>");
    }
    info(" La composition a été changé !");
}