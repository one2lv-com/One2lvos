/* Infinity Glass Universe Engine */

const scene = new THREE.Scene()

const camera = new THREE.PerspectiveCamera(
75,
window.innerWidth/window.innerHeight,
0.1,
1000
)

const renderer = new THREE.WebGLRenderer({antialias:true})

renderer.setSize(window.innerWidth,window.innerHeight)

document.body.appendChild(renderer.domElement)

/* star field */

const stars = new THREE.BufferGeometry()

const starCount = 2000

const starPositions = []

for(let i=0;i<starCount;i++){

starPositions.push(
(Math.random()-0.5)*2000,
(Math.random()-0.5)*2000,
(Math.random()-0.5)*2000
)

}

stars.setAttribute(
'position',
new THREE.Float32BufferAttribute(starPositions,3)
)

const starMaterial = new THREE.PointsMaterial({
color:0xffffff,
size:1
})

const starField = new THREE.Points(stars,starMaterial)

scene.add(starField)

/* breadcrumb nodes */

const nodes = []

const nodeMaterial = new THREE.MeshBasicMaterial({
color:0x00ffcc
})

for(let i=0;i<20;i++){

const geo = new THREE.SphereGeometry(1.5,16,16)

const node = new THREE.Mesh(geo,nodeMaterial)

node.position.set(
(Math.random()-0.5)*300,
(Math.random()-0.5)*200,
(Math.random()-0.5)*300
)

scene.add(node)

nodes.push(node)

}

/* lattice lines */

const lineMaterial = new THREE.LineBasicMaterial({
color:0x00ffff
})

for(let i=0;i<nodes.length;i++){

for(let j=i+1;j<nodes.length;j++){

if(Math.random()>0.85){

const points=[]

points.push(nodes[i].position)
points.push(nodes[j].position)

const geo = new THREE.BufferGeometry().setFromPoints(points)

const line = new THREE.Line(geo,lineMaterial)

scene.add(line)

}

}

}

camera.position.z = 120

/* animation */

function animate(){

requestAnimationFrame(animate)

/* rotate universe */

starField.rotation.y += 0.0002

/* pulse nodes */

const t = Date.now()*0.002

nodes.forEach((n,i)=>{

const scale = 1 + Math.sin(t+i)*0.4

n.scale.set(scale,scale,scale)

})

renderer.render(scene,camera)

}

animate()

/* resize */

window.addEventListener("resize",()=>{

camera.aspect = window.innerWidth/window.innerHeight
camera.updateProjectionMatrix()
renderer.setSize(window.innerWidth,window.innerHeight)

})
