import fs from "fs"

const MODULE_PATH = "./infinity-glass/modules"

export function lumenisBuild(prompt){

console.log("⚛️ Lumenis analyzing request:", prompt)

let code = ""

if(prompt.includes("sensor")){

code = `
#!/bin/bash
echo "[LUMENIS SENSOR MODULE]"
termux-sensor -n 1
`

}

else if(prompt.includes("reactor")){

code = `
#!/bin/bash
echo "[REACTOR STATUS]"
curl -s http://127.0.0.1:3000/api/status
`

}

else{

code = `
#!/bin/bash
echo "[LUMENIS MODULE]"
echo "Request: ${prompt}"
`

}

const name = prompt.replace(/ /g,"_") + ".sh"

fs.writeFileSync(\`\${MODULE_PATH}/\${name}\`,code)

console.log("Module created:",name)

return name

}
