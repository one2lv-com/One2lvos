// Lumenis AI Module

function lumenisThink(event, state){

    if(event === "combo")
        return "Opponent stunned — push pressure"

    if(event === "jumpSpam")
        return "Opponent favors aerial entry"

    if(event === "dodgeLeft")
        return "Cover dodge-left escape"

    return "Observing battlefield"
}

module.exports = { lumenisThink }
