'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const canvas = $('mapCanvas'), ctx = canvas.getContext('2d');
  const app = {nodes:[], edges:[], floors:[{id:0,name:'Ground Floor'}], currentFloor:0, selected:null, tool:'select', linkFrom:null, blockMode:false, zoom:1, panX:0, panY:0, drag:null, running:false, paused:false, done:false, tick:0, elapsedMs:0, lastFrame:0, accumulator:0, speed:3, remaining:{}, routes:{}, waves:{}, stranded:[], particles:[], evacuated:0, inTransit:0, events:[], history:[], autoIncidentDone:false, dirty:true, currentWave:null, holdForTransit:false, benchmark:[], saved:[], lastResult:null, totalPeople:0};
  const colors = {purple:'#9a8cff',cyan:'#5ad5e7',green:'#45d6a0',red:'#fb7185',amber:'#f4bd63',text:'#eaf0fa',muted:'#8fa0b8',edge:'#43536d',grid:'#2b3c55'};
  const nodeById = id => app.nodes.find(n => n.id === id);
  const edgeKey = (a,b) => [a,b].sort().join('::');
  const edgeByKey = k => app.edges.find(e => edgeKey(e.a,e.b) === k);
  const isExit = n => n.type === 'exit';
  const totalPopulation = () => app.nodes.filter(n=>n.type==='room').reduce((s,n)=>s+Math.max(0,Number(n.pop)||0),0);
  const roomNodes = () => app.nodes.filter(n=>n.type==='room');
  const exitNodes = () => app.nodes.filter(isExit);
  const clamp = (v,a,b) => Math.max(a,Math.min(b,v));
  const fmt = n => Number.isFinite(n) ? (Math.abs(n-Math.round(n))<.001?String(Math.round(n)):n.toFixed(1)) : '—';
  // Return a corridor segment clipped to the OUTSIDE edges of its endpoint room/exit boxes.
  // The graph stores node centres for routing, but the map must never draw corridors through them.
  function edgeSegment(e){
    const a=nodeById(e.a),b=nodeById(e.b); if(!a||!b)return [];
    if(e.vertical)return [{x:a.x,y:a.y,floor:a.floor??0},{x:b.x,y:b.y,floor:b.floor??0}];
    const dims=n=>n.type==='exit'?{rx:34,ry:25}:{rx:32,ry:30};
    const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;
    const da=dims(a),db=dims(b);
    const ta=1/Math.max(Math.abs(dx)/(da.rx||1),Math.abs(dy)/(da.ry||1),1e-6);
    const tb=1/Math.max(Math.abs(dx)/(db.rx||1),Math.abs(dy)/(db.ry||1),1e-6);
    return [{x:a.x+dx*ta,y:a.y+dy*ta,floor:a.floor??0},{x:b.x-dx*tb,y:b.y-dy*tb,floor:b.floor??0}];
  }
  function routePolyline(route){
    const pts=[]; for(const e of route.edgeRefs){const seg=edgeSegment(e);if(!seg.length)continue;if(!pts.length||pts[pts.length-1].floor!==seg[0].floor||Math.hypot(pts[pts.length-1].x-seg[0].x,pts[pts.length-1].y-seg[0].y)>0.1)pts.push(seg[0]);pts.push(seg[1]);}
    return pts;
  }

  function sampleScenario(kind='sample') {
    let ns=[], es=[];
    if(kind==='sample') {
      const coords={A:[90,90,25],B:[265,78,20],C:[455,88,30],D:[665,83,15],E:[105,265,20],F:[445,270,25],G:[690,260,15],H:[245,435,20],I:[520,430,30]};
      Object.entries(coords).forEach(([id,p])=>ns.push({id,x:p[0],y:p[1],type:'room',pop:p[2],floor:0}));
      ns.push({id:'EXIT1',x:850,y:260,type:'exit',pop:0,capacity:30,floor:0},{id:'EXIT2',x:680,y:490,type:'exit',pop:0,capacity:20,floor:0});
      const links=[['A','B',1,25],['B','C',1,20],['C','D',1,20,true],['A','E',1,18],['C','F',1,15],['D','G',1,15],['E','H',2,18],['F','I',1,22],['G','EXIT1',1,30],['H','I',1,20],['I','EXIT1',1,30],['I','EXIT2',1,20]];
      links.forEach(([a,b,w,c,blocked])=>es.push({a,b,w,c,blocked:!!blocked}));
    } else if(kind==='multifloor') {
      const rnd=(a,b)=>Math.floor(Math.random()*(b-a+1))+a;
      const floorRooms=[
        [{id:'A',x:100,y:100,pop:18},{id:'B',x:300,y:100,pop:22},{id:'C',x:500,y:100,pop:16},{id:'D',x:300,y:300,pop:24}],
        [{id:'E',x:100,y:100,pop:20},{id:'F',x:300,y:100,pop:26},{id:'G',x:500,y:100,pop:18},{id:'H',x:300,y:300,pop:20}],
        [{id:'I',x:100,y:100,pop:15},{id:'J',x:300,y:100,pop:21},{id:'K',x:500,y:100,pop:19},{id:'L',x:300,y:300,pop:17}]
      ];
      floorRooms.forEach((rooms,floor)=>rooms.forEach(r=>ns.push({id:r.id,x:r.x,y:r.y,type:'room',pop:r.pop,floor})));
      ns.push({id:'EXIT1',x:880,y:180,type:'exit',pop:0,capacity:28,floor:0},{id:'EXIT2',x:880,y:440,type:'exit',pop:0,capacity:22,floor:0});
      const add=(a,b,w,c,vertical=false,blocked=false)=>es.push({a,b,w,c,vertical,blocked});
      // Ground-floor circulation and exits.
      add('A','B',1,24);add('B','C',1,20);add('B','D',1.5,18);add('C','EXIT1',1.5,28);add('D','EXIT2',1.2,22);
      // First-floor circulation.
      add('E','F',1,22);add('F','G',1,20);add('F','H',1.5,18);
      // Third-floor circulation.
      add('I','J',1,20);add('J','K',1,18);add('J','L',1.5,18);
      // Stairwell 1 joins every adjacent floor; landings occupy the same schematic coordinates on each floor.
      const stairs=[
        {id:'STAIR-A-G',floor:0,x:700,y:350},{id:'STAIR-A-1',floor:1,x:700,y:350},{id:'STAIR-A-2',floor:2,x:700,y:350}
      ];
      stairs.forEach(n=>ns.push({...n,type:'stair',pop:0,capacity:20}));
      add('D','STAIR-A-G',1.2,20);add('STAIR-A-G','STAIR-A-1',2,20,true);add('STAIR-A-1','STAIR-A-2',2,20,true);
      add('H','STAIR-A-1',1.2,20);add('L','STAIR-A-2',1.2,20);
      // A second stairwell provides an alternate vertical path.
      const stairsB=[
        {id:'STAIR-B-G',floor:0,x:700,y:480},{id:'STAIR-B-1',floor:1,x:700,y:480},{id:'STAIR-B-2',floor:2,x:700,y:480}
      ];
      stairsB.forEach(n=>ns.push({...n,type:'stair',pop:0,capacity:20}));
      add('C','STAIR-B-G',1.4,18);add('STAIR-B-G','STAIR-B-1',2.2,18,true);add('STAIR-B-1','STAIR-B-2',2.2,18,true);
      add('G','STAIR-B-1',1.4,18);add('K','STAIR-B-2',1.4,18);
    } else {
      const count=kind==='dense'?12:6+Math.floor(Math.random()*9), rnd=(a,b)=>Math.floor(Math.random()*(b-a+1))+a;
      for(let i=0;i<count;i++){const cols=4;ns.push({id:String.fromCharCode(65+i),x:75+(i%cols)*245+rnd(-20,20),y:65+Math.floor(i/cols)*150+rnd(-12,12),type:'room',pop:kind==='dense'?rnd(20,55):rnd(8,36),floor:0});}
      const exCount=kind==='dense'?3:2;
      for(let i=0;i<exCount;i++)ns.push({id:'EXIT'+(i+1),x:890,y:80+i*205,type:'exit',pop:0,capacity:kind==='dense'?rnd(12,24):rnd(18,35),floor:0});
      const add=(a,b,w,c,blocked=false)=>{if(a!==b&&!es.some(e=>edgeKey(e.a,e.b)===edgeKey(a,b)))es.push({a,b,w,c,blocked});};
      // A chain backbone guarantees a connected room network before failures.
      for(let i=1;i<count;i++)add(ns[i-1].id,ns[i].id,rnd(1,3),kind==='dense'?rnd(8,18):rnd(12,28));
      for(let i=0;i<Math.floor(count*0.7);i++){let a=rnd(0,count-1),b=rnd(0,count-1);if(a!==b)add(ns[a].id,ns[b].id,rnd(1,3),kind==='dense'?rnd(8,18):rnd(12,28));}
      for(let i=0;i<exCount;i++){add(ns[rnd(0,count-1)].id,'EXIT'+(i+1),1,rnd(14,30));add(ns[rnd(0,count-1)].id,'EXIT'+(i+1),1,rnd(14,30));}
      if(es.length>3&&Math.random()<.75)es[rnd(0,es.length-1)].blocked=true;
    }
    app.nodes=ns;app.edges=es.map(e=>({...e,vertical:!!e.vertical}));app.floors=kind==='multifloor'?[{id:0,name:'Ground Floor'},{id:1,name:'Floor 2'},{id:2,name:'Floor 3'}]:[{id:0,name:'Ground Floor'}];app.currentFloor=0;app.selected=null;app.linkFrom=null;app.remaining={};app.routes={};app.waves={};app.stranded=[];app.particles=[];app.events=[];app.history=[];app.evacuated=0;app.inTransit=0;app.tick=0;app.elapsedMs=0;app.running=false;app.paused=false;app.done=false;app.autoIncidentDone=false;app.currentWave=null;app.holdForTransit=false;app.dirty=true;app.lastResult=null;app.totalPeople=totalPopulation();app.zoom=1;app.panX=0;app.panY=0;
    app.nodes.forEach(n=>{if(n.type==='room')app.remaining[n.id]=n.pop;});
    $('autoIncident').checked=false; $('runBtn').innerHTML='<span>▶</span> Run simulation'; $('pauseBtn').disabled=true; $('pauseBtn').textContent='Ⅱ Pause simulation';
    clearEvents(); logEvent('Scenario loaded',kind==='sample'?'Reference campus loaded with one blocked corridor.':kind==='dense'?'High-density stress test generated.':kind==='multifloor'?'Three-floor campus generated with two stairwells.':'Randomized building generated.','info');
    app.dirty=true; renderAll(); planRoutes(); draw(); updateStats();
  }

  function adjacency(includeBlocked=false) {
    const adj=new Map(app.nodes.map(n=>[n.id,[]]));
    app.edges.forEach(e=>{if(includeBlocked||!e.blocked){if(adj.has(e.a)&&adj.has(e.b)){adj.get(e.a).push({to:e.b,edge:e});adj.get(e.b).push({to:e.a,edge:e});}}});
    return adj;
  }
  function routeFrom(source, strategy) {
    const adj=adjacency(false), dist=new Map(app.nodes.map(n=>[n.id,Infinity])), prev=new Map(), used=new Set();dist.set(source,0);
    while(used.size<app.nodes.length){let u=null,best=Infinity;for(const n of app.nodes){if(!used.has(n.id)&&dist.get(n.id)<best){u=n.id;best=dist.get(n.id);}}if(u===null)break;used.add(u);
      for(const {to,edge} of adj.get(u)||[]){let cost=edge.w;if(strategy==='balanced')cost=edge.w*(1+Math.max(0,20-edge.c)/35)+(edge.c<12?0.6:0);if(strategy==='capacity')cost=edge.w*(1+10/Math.max(1,edge.c));const nd=best+cost;if(nd<dist.get(to)){dist.set(to,nd);prev.set(to,{from:u,edge});}}
    }
    let target=null,targetDist=Infinity;for(const ex of exitNodes()){if(dist.get(ex.id)<targetDist){target=ex.id;targetDist=dist.get(ex.id);}}
    if(!target||!Number.isFinite(targetDist))return null;
    const path=[target],edges=[];let cur=target,guard=0;while(cur!==source&&guard++<app.nodes.length+1){const p=prev.get(cur);if(!p)return null;edges.unshift(p.edge);path.unshift(p.from);cur=p.from;}
    if(cur!==source)return null;
    const bottleneck=edges.length?Math.min(...edges.map(e=>e.c),...edges.filter(e=>isExit(nodeById(e.a))||isExit(nodeById(e.b))).map(e=>e.c)):Infinity;
    return {source,exit:target,path,edges:edges.map(e=>edgeKey(e.a,e.b)),edgeRefs:edges, cost:targetDist, eta:edges.reduce((s,e)=>s+e.w,0), bottleneck:Number.isFinite(bottleneck)?bottleneck:1};
  }
  function colorRoutes(routes) {
    const ids=Object.keys(routes), conflict={};ids.forEach(id=>conflict[id]=new Set());
    for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){const a=routes[ids[i]],b=routes[ids[j]];if(a.edges.some(k=>b.edges.includes(k))){conflict[ids[i]].add(ids[j]);conflict[ids[j]].add(ids[i]);}}
    const order=ids.slice().sort((a,b)=>conflict[b].size-conflict[a].size);const color={};for(const id of order){const used=new Set([...conflict[id]].map(n=>color[n]).filter(n=>n!==undefined));let c=0;while(used.has(c))c++;color[id]=c;}
    return {color,conflict};
  }
  function planRoutes() {
    const strategy=$('strategySelect').value;app.routes={};app.stranded=[];
    roomNodes().forEach(n=>{if((app.remaining[n.id]??n.pop)>0){const r=routeFrom(n.id,strategy);if(r)app.routes[n.id]=r;else app.stranded.push(n.id);}});
    const c=colorRoutes(app.routes);app.waves=c.color;app.conflicts=c.conflict;app.dirty=false;
    updateRouteList();updateNetworkHealth();draw();return app.routes;
  }
  function refreshPlan() {
    if(app.running && app.particles.length>0){app.holdForTransit=true;app.currentWave=null;}
    app.dirty=true;
    planRoutes();
  }
  function estimatedDuration(routes=app.routes,remaining=app.remaining) {
    const {color}=colorRoutes(routes), waves={};Object.keys(routes).forEach(id=>(waves[color[id]]??=[]).push(id));let duration=0;
    Object.keys(waves).map(Number).sort((a,b)=>a-b).forEach(w=>{const members=waves[w];let waveTicks=0;members.forEach(id=>{const r=routes[id],p=Math.max(0,remaining[id]??nodeById(id).pop);waveTicks=Math.max(waveTicks,Math.ceil(p/Math.max(1,r.bottleneck))+r.eta);});duration+=waveTicks;});return duration;
  }
  function connectivity() {const adj=adjacency(false), rooms=roomNodes(), exits=exitNodes();let reachable=0;const per={};rooms.forEach(r=>{const seen=new Set([r.id]),q=[r.id];while(q.length){const u=q.shift();for(const n of (adj.get(u)||[])){if(!seen.has(n.to)){seen.add(n.to);q.push(n.to);}}}per[r.id]=exits.some(e=>seen.has(e.id));if(per[r.id])reachable++;});return {reachable,total:rooms.length,per};}
  function maxFlowRate() {
    // Directed residual network: super-source -> rooms -> corridors -> exits -> sink.
    const nodes=app.nodes.map(n=>n.id), S='__SOURCE__', T='__SINK__', cap=new Map();const set=(u,v,c)=>{if(!cap.has(u))cap.set(u,new Map());cap.get(u).set(v,(cap.get(u).get(v)||0)+c);if(!cap.has(v))cap.set(v,new Map());if(!cap.get(v).has(u))cap.get(v).set(u,0);};
    app.edges.filter(e=>!e.blocked).forEach(e=>{set(e.a,e.b,e.c);set(e.b,e.a,e.c);});roomNodes().forEach(r=>set(S,r.id,Math.max(0,r.pop)));exitNodes().forEach(e=>set(e.id,T,Math.max(1,e.capacity||20)));
    let flow=0;for(;;){const parent=new Map([[S,null]]),q=[S];while(q.length&&!parent.has(T)){const u=q.shift();for(const [v,c] of cap.get(u)||[]){if(c>0&&!parent.has(v)){parent.set(v,u);q.push(v);}}}if(!parent.has(T))break;let bn=Infinity,v=T;while(parent.get(v)!==null){const u=parent.get(v);bn=Math.min(bn,cap.get(u).get(v));v=u;}v=T;while(parent.get(v)!==null){const u=parent.get(v);cap.get(u).set(v,cap.get(u).get(v)-bn);cap.get(v).set(u,(cap.get(v).get(u)||0)+bn);v=u;}flow+=bn;}
    return flow;
  }
  function topBottleneck() {
    const freq=new Map();Object.values(app.routes).forEach(r=>r.edges.forEach(k=>freq.set(k,(freq.get(k)||0)+1)));
    const candidates=app.edges.filter(e=>!e.blocked).map(e=>({e,score:(freq.get(edgeKey(e.a,e.b))||0)*100/Math.max(1,e.c)})).sort((a,b)=>b.score-a.score);
    if(!candidates.length)return null;return candidates[0];
  }
  function updateNetworkHealth(){const con=connectivity(),rate=maxFlowRate(),tb=topBottleneck();$('reachability').textContent=`${con.reachable}/${con.total} rooms`;$('reachFill').style.width=(con.total?con.reachable/con.total*100:0)+'%';$('exitThroughput').textContent=`${fmt(rate)} people / tick`;$('footNetwork').textContent=con.reachable===con.total?'Connected':'Disconnected';$('connectText').textContent=con.reachable===con.total?'All rooms connected':`${con.total-con.reachable} room(s) isolated`;$('connectDot').className='tiny-dot '+(con.reachable===con.total?'green':'red');$('healthIndicator').innerHTML=`<i style="background:${con.reachable===con.total?'var(--green)':'var(--red)'}"></i> ${con.reachable===con.total?'Network reachable':'Needs attention'}`;
    const bars=$('exitBars');bars.innerHTML='';const max=Math.max(1,...exitNodes().map(e=>e.capacity||20));exitNodes().forEach(e=>{const b=document.createElement('i');b.style.height=(Math.max(8,(e.capacity||20)/max*100))+'%';b.title=e.id+': '+(e.capacity||20)+' people/tick';bars.appendChild(b);});if(tb){$('bottleneckTitle').textContent=`Potential bottleneck: ${tb.e.a} ↔ ${tb.e.b}`;$('bottleneckText').textContent=`Capacity ${tb.e.c}/tick · used by ${Object.values(app.routes).filter(r=>r.edges.includes(edgeKey(tb.e.a,tb.e.b))).length} planned route(s). This is a heuristic indicator, not a certified safety finding.`;}else{$('bottleneckTitle').textContent='No open corridors';$('bottleneckText').textContent='Add or unblock a corridor to enable routing.';}}
  function updateRouteList(){const list=$('routeList'),ids=Object.keys(app.routes).sort();$('routeCount').textContent=`${ids.length} route${ids.length===1?'':'s'}`;if(!ids.length){list.innerHTML=`<div class="empty-state"><div class="empty-glyph">⌁</div><b>No reachable routes</b><span>Check exits and blocked corridors.</span></div>`;return;}list.innerHTML='';ids.forEach(id=>{const r=app.routes[id],room=nodeById(id),remaining=app.remaining[id]??room.pop;const el=document.createElement('div');el.className='route-item';el.innerHTML=`<div class="route-node">${escapeHtml(id)}</div><div class="route-main"><b>${remaining} people · Exit ${escapeHtml(r.exit.replace('EXIT',''))}</b><div class="route-path">${r.path.map(escapeHtml).join(' → ')}</div><div class="route-status">${fmt(r.bottleneck)} people/tick · ${fmt(r.eta)} min path</div></div><div class="route-eta">${fmt(r.eta)}<small>walk time</small></div>`;el.onclick=()=>selectElement('node',id);list.appendChild(el);});app.stranded.forEach(id=>{const el=document.createElement('div');el.className='route-item';el.innerHTML=`<div class="route-node" style="background:#482433;color:#ff9cac">!</div><div class="route-main"><b>${escapeHtml(id)} · no route</b><div class="route-path">No open path to an exit</div><div class="route-status stranded">Action required</div></div><div class="route-eta">—<small>stranded</small></div>`;el.onclick=()=>selectElement('node',id);list.appendChild(el);});}
  function updateStats(){const total=totalPopulation(),ev=app.evacuated,pc=total?ev/total*100:0;app.totalPeople=total;$('mPeople').textContent=total;$('mRooms').textContent=`${roomNodes().length} rooms`;$('mEvacuated').textContent=Math.min(total,Math.round(ev));$('mPercent').textContent=Math.round(pc)+'%';$('evacProgress').style.width=pc+'%';$('mTime').textContent=app.tick.toFixed(1);$('mStranded').textContent=app.stranded.length;$('mState').textContent=app.running?(app.paused?'Paused':'In progress'):app.done?'Simulation complete':'Ready to run';$('footNodes').textContent=app.nodes.filter(n=>(n.floor??0)===app.currentFloor).length;$('footEdges').textContent=app.edges.filter(e=>!e.vertical&&((nodeById(e.a)?.floor??0)===app.currentFloor)&&((nodeById(e.b)?.floor??0)===app.currentFloor)).length;$('canvasEmpty').hidden=app.nodes.some(n=>(n.floor??0)===app.currentFloor);updateFloorControls();}
  function clearEvents(){app.events=[];$('eventLog').innerHTML='';$('eventCount').textContent='0';}
  function logEvent(title,message,type='info'){app.events.unshift({title,message,type,time:app.tick});app.events=app.events.slice(0,30);$('eventCount').textContent=String(app.events.length);$('eventLog').innerHTML='';app.events.forEach(e=>{const d=document.createElement('div');d.className='event '+(e.type==='warning'?'warning':e.type==='danger'?'danger':'');d.innerHTML=`<div class="event-time">T+${fmt(e.time)}</div><div class="event-msg"><span class="event-icon">${e.type==='danger'?'✕':e.type==='warning'?'⚠':'•'}</span><b>${escapeHtml(e.title)}</b><br>${escapeHtml(e.message)}</div>`;$('eventLog').appendChild(d);});}
  function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

  function startSimulation(){if(app.running){return;}if(!roomNodes().length||!exitNodes().length){toast('Building incomplete','Add at least one room and one exit.','error');return;}if(!app.nodes.some(n=>n.type==='room'&&n.pop>0)){toast('No occupants','Set a positive population for at least one room.','error');return;}
    app.remaining={};roomNodes().forEach(n=>app.remaining[n.id]=n.pop);app.particles=[];app.evacuated=0;app.inTransit=0;app.tick=0;app.accumulator=0;app.elapsedMs=0;app.running=true;app.paused=false;app.done=false;app.autoIncidentDone=false;app.currentWave=null;app.holdForTransit=false;app.history=[];app.lastResult=null;app.speed=+$('speedRange').value;clearEvents();planRoutes();logEvent('Simulation started',`${$('strategySelect').selectedOptions[0].text} · ${totalPopulation()} occupants.`);$('runBtn').innerHTML='<span>Ⅱ</span> Pause';$('pauseBtn').disabled=false;$('pauseBtn').textContent='Ⅱ Pause simulation';updateStats();}
  function togglePause(){if(!app.running)return;app.paused=!app.paused;$('runBtn').innerHTML=app.paused?'<span>▶</span> Resume':'<span>Ⅱ</span> Pause';$('pauseBtn').textContent=app.paused?'▶ Resume simulation':'Ⅱ Pause simulation';}
  function finishSimulation(){app.running=false;app.paused=false;app.done=true;$('runBtn').innerHTML='<span>↻</span> Run again';$('pauseBtn').disabled=true;$('pauseBtn').textContent='Ⅱ Pause simulation';const strandedPeople=app.stranded.reduce((s,id)=>s+(app.remaining[id]||0),0);logEvent('Simulation complete',`${app.evacuated} people reached exits; ${strandedPeople} remain in unreachable rooms. Elapsed model time: ${app.tick} ticks.`,strandedPeople?'warning':'info');app.lastResult={strategy:$('strategySelect').value,durationTicks:app.tick,evacuated:app.evacuated,stranded:app.stranded.slice(),total:totalPopulation()};updateStats();}
  function makeParticle(route,count,waveId){const points=routePolyline(route);if(points.length<2){app.evacuated+=count;return;}const distance=points.slice(1).reduce((s,p,i)=>s+Math.hypot(p.x-points[i].x,p.y-points[i].y),0);app.particles.push({points,progress:0,duration:Math.max(1,route.eta)*1.2,count,dist:distance,route:route.path.join(' → '),waveId});app.inTransit+=count;}
  function doTick(){if(!app.running||app.paused)return;app.tick+=1;
    if($('autoIncident').checked&&!app.autoIncidentDone&&app.tick>=Math.max(3,Math.ceil(estimatedDuration()/5))){const freq=new Map();Object.values(app.routes).forEach(r=>r.edges.forEach(k=>freq.set(k,(freq.get(k)||0)+1)));const candidates=app.edges.filter(e=>!e.blocked&&!(isExit(nodeById(e.a))&&isExit(nodeById(e.b)))).sort((a,b)=>(freq.get(edgeKey(b.a,b.b))||0)/(b.c||1)-(freq.get(edgeKey(a.a,a.b))||0)/(a.c||1));if(candidates.length){candidates[0].blocked=true;app.autoIncidentDone=true;app.dirty=true;logEvent('Incident injected',`Corridor ${candidates[0].a} ↔ ${candidates[0].b} blocked automatically. Replanning routes.`, 'danger');}}
    const wasDirty=app.dirty;if(app.dirty)planRoutes();
    if(wasDirty&&app.running&&app.particles.length>0)app.holdForTransit=true;
    if(app.holdForTransit){if(app.particles.length>0){updateStats();return;}app.holdForTransit=false;app.currentWave=null;}
    const active=Object.keys(app.routes).filter(id=>(app.remaining[id]||0)>0);if(!active.length){if(app.particles.length===0)finishSimulation();updateStats();return;}
    const colorsNow=app.waves;
    if(app.currentWave===null){app.currentWave=Math.min(...active.map(id=>colorsNow[id]??0));}
    const inWave=active.filter(id=>(colorsNow[id]??0)===app.currentWave);
    if(!inWave.length){if(app.particles.length>0){updateStats();return;}app.currentWave=null;updateStats();return;}
    let moved=0;
    inWave.forEach(id=>{const r=app.routes[id],amount=Math.min(app.remaining[id]||0,Math.max(1,Math.floor(r.bottleneck)));if(amount>0){app.remaining[id]-=amount;makeParticle(r,amount,app.currentWave);moved+=amount;}});
    const waveStillHasPeople=roomNodes().some(n=>(app.remaining[n.id]||0)>0&&(colorsNow[n.id]??-1)===app.currentWave);
    if(!waveStillHasPeople&&app.particles.length===0)app.currentWave=null;
    if(!moved){app.dirty=true;const any=roomNodes().some(n=>(app.remaining[n.id]||0)>0&&app.routes[n.id]);if(!any&&app.particles.length===0){finishSimulation();}}
    app.history.push({tick:app.tick,evacuated:app.evacuated,remaining:Object.values(app.remaining).reduce((a,b)=>a+b,0)});if(app.history.length>1000)app.history.shift();updateStats();draw();
  }
  function advanceParticles(dt){for(let i=app.particles.length-1;i>=0;i--){const p=app.particles[i];p.progress+=dt/Math.max(350,p.duration*1000/(app.speed/3));if(p.progress>=1){app.evacuated+=p.count;app.inTransit-=p.count;app.particles.splice(i,1);}}}

  // Canvas renderer. Model coordinates are independent of viewport size; zoom and pan are presentation-only.
  let view={scale:1,ox:0,oy:0,w:1000,h:560};
  function resizeCanvas(){const r=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;canvas.width=Math.max(1,Math.floor(r.width*dpr));canvas.height=Math.max(1,Math.floor(r.height*dpr));ctx.setTransform(dpr,0,0,dpr,0,0);view.w=r.width;view.h=r.height;const fit=Math.min((r.width-40)/1000,(r.height-40)/560);view.scale=fit*app.zoom;view.ox=(r.width-1000*view.scale)/2+app.panX;view.oy=(r.height-560*view.scale)/2+app.panY;$('zoomLabel').textContent=Math.round(app.zoom*100)+'%';draw();}
  function toScreen(p){return {x:view.ox+p.x*view.scale,y:view.oy+p.y*view.scale};}function toModel(x,y){return {x:(x-view.ox)/view.scale,y:(y-view.oy)/view.scale};}
  function draw(){
    const r=canvas.getBoundingClientRect();if(!r.width||!r.height)return;
    const dpr=window.devicePixelRatio||1;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,r.width,r.height);
    ctx.save();ctx.translate(view.ox,view.oy);ctx.scale(view.scale,view.scale);
    // Calm technical map background: a grid and three labelled planning zones.
    ctx.fillStyle='#0b1424';ctx.fillRect(0,0,1000,560);
    ctx.strokeStyle='#1b2a40';ctx.lineWidth=1;ctx.globalAlpha=.68;
    for(let x=20;x<1000;x+=25){ctx.beginPath();ctx.moveTo(x,20);ctx.lineTo(x,540);ctx.stroke();}
    for(let y=20;y<560;y+=25){ctx.beginPath();ctx.moveTo(20,y);ctx.lineTo(980,y);ctx.stroke();}
    ctx.globalAlpha=1;
    const floorTitle=(app.floors.find(f=>f.id===app.currentFloor)||{name:floorName({id:app.currentFloor})}).name;
    const zones=[{x:35,y:35,w:715,h:145,label:'NORTH WING',fill:'#6e62bd'},{x:35,y:190,w:715,h:165,label:'CENTRAL WING',fill:'#3f8ca1'},{x:35,y:365,w:715,h:160,label:'SOUTH WING',fill:'#3d9279'}];
    zones.forEach(z=>{ctx.fillStyle=z.fill+'0b';ctx.fillRect(z.x,z.y,z.w,z.h);ctx.strokeStyle=z.fill+'55';ctx.setLineDash([5,7]);ctx.strokeRect(z.x,z.y,z.w,z.h);ctx.setLineDash([]);ctx.fillStyle=z.fill;ctx.font='600 10px "DM Mono",monospace';ctx.textAlign='left';ctx.fillText(z.label,z.x+10,z.y+17);});
    ctx.fillStyle='#aab9d0';ctx.font='600 11px "DM Mono",monospace';ctx.textAlign='left';ctx.fillText(floorTitle.toUpperCase(),48,535);
    // Only label an exit collection zone on floors that actually contain exits.
    if(app.nodes.some(n=>n.type==='exit'&&(n.floor??0)===app.currentFloor)){ctx.fillStyle='#45d6a008';ctx.fillRect(790,35,175,490);ctx.strokeStyle='#45d6a055';ctx.setLineDash([5,7]);ctx.strokeRect(790,35,175,490);ctx.setLineDash([]);ctx.fillStyle='#6fe2bc';ctx.font='600 10px "DM Mono",monospace';ctx.textAlign='center';ctx.fillText('SAFE EXITS',877,54);} 
    const routeEdges=new Set();Object.values(app.routes).forEach(rt=>rt.edges.forEach(k=>routeEdges.add(k)));
    const visibleNodes=app.nodes.filter(n=>(n.floor??0)===app.currentFloor);const visibleIds=new Set(visibleNodes.map(n=>n.id));
    // Corridors are intentionally shown as network links, not as architectural walls.
    app.edges.forEach(e=>{
      const a=nodeById(e.a),b=nodeById(e.b);if(!a||!b||e.vertical||!visibleIds.has(e.a)||!visibleIds.has(e.b))return;
      const k=edgeKey(e.a,e.b),active=routeEdges.has(k)&&!e.blocked,selected=app.selected?.type==='edge'&&app.selected.key===k;
      const seg=edgeSegment(e);if(seg.length<2)return;
      ctx.beginPath();ctx.moveTo(seg[0].x,seg[0].y);ctx.lineTo(seg[1].x,seg[1].y);
      ctx.lineCap='round';ctx.lineWidth=selected?9:active?7:4.5;ctx.strokeStyle=e.blocked?'#fb7185':active?'#45d6a0':'#536783';ctx.globalAlpha=e.blocked?1:active?.95:.62;
      if(e.blocked)ctx.setLineDash([10,7]);else ctx.setLineDash([]);ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=1;
      if(active&&!selected){ctx.beginPath();ctx.moveTo(seg[0].x,seg[0].y);ctx.lineTo(seg[1].x,seg[1].y);ctx.lineWidth=2;ctx.strokeStyle='#b2ffe4';ctx.globalAlpha=.85;ctx.stroke();ctx.globalAlpha=1;}
      const mx=(seg[0].x+seg[1].x)/2,my=(seg[0].y+seg[1].y)/2,label=e.blocked?'BLOCKED':`${e.c}/tick · ${e.w}m`,tw=ctx.measureText(label).width;
      if($('showLabels').checked){ctx.font='10px "DM Mono",monospace';const w=ctx.measureText(label).width+14;ctx.fillStyle='#101b2c';ctx.beginPath();ctx.roundRect(mx-w/2,my-22,w,17,5);ctx.fill();ctx.strokeStyle=e.blocked?'#713747':active?'#286b54':'#30425d';ctx.lineWidth=1;ctx.stroke();ctx.fillStyle=e.blocked?'#ff9cac':active?'#8de9c8':'#a6b7ce';ctx.textAlign='center';ctx.fillText(label,mx,my-10);}
    });
    // Animated groups stay attached to the exact route points returned by the planner.
    app.particles.forEach(p=>{
      let target=p.progress*p.dist,idx=0;while(idx<p.points.length-2){const a=p.points[idx],b=p.points[idx+1],len=Math.hypot(b.x-a.x,b.y-a.y);if(target<=len)break;target-=len;idx++;}
      const a=p.points[idx],b=p.points[Math.min(idx+1,p.points.length-1)],len=Math.hypot(b.x-a.x,b.y-a.y)||1,t=clamp(target/len,0,1),x=a.x+(b.x-a.x)*t,y=a.y+(b.y-a.y)*t;
      const particleFloor=t<0.5?(a.floor??0):(b.floor??a.floor??0);if(particleFloor!==app.currentFloor)return;
      const count=Math.min(5,Math.max(1,Math.ceil(p.count/8)));for(let i=0;i<count;i++){const off=(i-(count-1)/2)*8;ctx.beginPath();ctx.arc(x+off,y+(i%2?2:-2),3.6,0,Math.PI*2);ctx.fillStyle=i===0?'#e2fff5':'#45d6a0';ctx.shadowColor='#45d6a0';ctx.shadowBlur=8;ctx.fill();ctx.shadowBlur=0;}
    });
    // Room nodes and exits use consistent labels and distinct silhouettes.
    visibleNodes.forEach(n=>{
      const selected=app.selected?.type==='node'&&app.selected.id===n.id,rem=app.remaining[n.id]??n.pop,frac=n.type==='room'&&n.pop>0?rem/n.pop:0;
      const isE=n.type==='exit',isStair=n.type==='stair';let fill=n.type==='exit'?'#126b60':isStair?'#79551d':(!app.running&&!app.done?'#51489b':`hsl(${120*(1-frac)} 52% ${24+frac*8}%)`);if(app.stranded.includes(n.id))fill='#7e2e45';
      const w=isE?64:isStair?68:58,h=isE?46:isStair?50:54,x=n.x-w/2,y=n.y-h/2;
      if(selected){ctx.beginPath();ctx.roundRect(x-7,y-7,w+14,h+14,14);ctx.strokeStyle='#c8c0ff';ctx.lineWidth=2;ctx.setLineDash([4,4]);ctx.stroke();ctx.setLineDash([]);}
      ctx.shadowColor=isE?'#45d6a055':'#8b7cff25';ctx.shadowBlur=selected?18:8;ctx.beginPath();ctx.roundRect(x,y,w,h,isE?10:9);ctx.fillStyle=fill;ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle=selected?'#d5ceff':isE?'#5de1bd':isStair?'#f4bd63':'#9d92ff';ctx.lineWidth=selected?2.5:1.2;ctx.stroke();
      ctx.textAlign='center';ctx.fillStyle='#f5f7ff';ctx.font='700 12px Manrope,sans-serif';ctx.fillText(isE?'EXIT':isStair?'↕ STAIR':n.id,n.x,n.y-4);
      ctx.fillStyle=isE?'#baffeb':'#d0d9e8';ctx.font='10px "DM Mono",monospace';ctx.fillText(isE?`${n.capacity||20}/tick`:isStair?stairDestinationLabel(n):app.running||app.done?`${Math.max(0,Math.round(rem))}/${n.pop}`:`${n.pop} people`,n.x,n.y+12);
      if(app.stranded.includes(n.id)){ctx.beginPath();ctx.arc(x+w-2,y+2,8,0,Math.PI*2);ctx.fillStyle=colors.red;ctx.fill();ctx.fillStyle='#fff';ctx.font='bold 10px Manrope';ctx.fillText('!',x+w-2,y+6);}
    });
    ctx.restore();
  }

  function canvasPoint(ev){const r=canvas.getBoundingClientRect();return {x:ev.clientX-r.left,y:ev.clientY-r.top};}
  function hitNode(p){const m=toModel(p.x,p.y);return app.nodes.filter(n=>(n.floor??0)===app.currentFloor).slice().reverse().find(n=>Math.abs(n.x-m.x)<(n.type==='exit'?34:n.type==='stair'?36:28)&&Math.abs(n.y-m.y)<29)||null;}
  function pointSegmentDistance(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,l=dx*dx+dy*dy||1,t=clamp(((p.x-a.x)*dx+(p.y-a.y)*dy)/l,0,1);return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);}
  function hitEdge(p){const m=toModel(p.x,p.y);return app.edges.filter(e=>!e.vertical&&(nodeById(e.a)?.floor??0)===app.currentFloor&&(nodeById(e.b)?.floor??0)===app.currentFloor).slice().reverse().find(e=>{const a=nodeById(e.a),b=nodeById(e.b);return a&&b&&pointSegmentDistance(m,a,b)<9;})||null;}
  function floorName(f){return f.id===0?'Ground Floor':`Floor ${f.id+1}`;}
  function stairDestinationLabel(n){const e=app.edges.find(x=>x.vertical&&(x.a===n.id||x.b===n.id));if(!e)return 'No link';const other=nodeById(e.a===n.id?e.b:e.a);return other?`to ${floorName(app.floors.find(f=>f.id===(other.floor??0))||{id:other.floor??0})}`:'No link';}
  function updateFloorControls(){const sel=$('floorSelect');if(!sel)return;const old=app.currentFloor;sel.innerHTML='';app.floors.slice().sort((a,b)=>a.id-b.id).forEach(f=>{const o=document.createElement('option');o.value=String(f.id);o.textContent=f.name||floorName(f);sel.appendChild(o);});if(app.floors.some(f=>f.id===old))sel.value=String(old);else{app.currentFloor=app.floors[0]?.id??0;sel.value=String(app.currentFloor);}const current=app.floors.find(f=>f.id===app.currentFloor);$('floorCount').textContent=`${app.floors.length} floor${app.floors.length===1?'':'s'}`;$('removeFloorBtn').disabled=app.floors.length<=1;$('addStairLinkBtn').disabled=!app.floors.some(f=>f.id===app.currentFloor+1);}
  function uniqueStairId(floor){let i=1,id;do{id=`STAIR-F${floor+1}-${i++}`;}while(nodeById(id));return id;}
  function addStairConnection(floorA,floorB,x=520,y=280){if(Math.abs(floorA-floorB)!==1){toast('Adjacent floors only','Connect staircase landings between adjacent floors.','error');return false;}const a={id:uniqueStairId(floorA),x:clamp(x,60,940),y:clamp(y,75,500),type:'stair',pop:0,capacity:20,floor:floorA};const b={id:uniqueStairId(floorB),x:a.x,y:a.y,type:'stair',pop:0,capacity:20,floor:floorB};app.nodes.push(a,b);app.edges.push({a:a.id,b:b.id,w:2,c:20,blocked:false,vertical:true});app.dirty=true;logEvent('Stair connection added',`${a.id} on ${floorName(app.floors.find(f=>f.id===floorA)||{id:floorA})} connects to ${b.id} on ${floorName(app.floors.find(f=>f.id===floorB)||{id:floorB})}.`);return true;}
  function addFloor(){if(app.running){toast('Pause simulation','Add floors while the simulation is stopped.','error');return;}const maxId=Math.max(-1,...app.floors.map(f=>f.id)),id=maxId+1;const previous=maxId;app.floors.push({id,name:floorName({id})});if(previous>=0)addStairConnection(previous,id);app.currentFloor=id;updateFloorControls();refreshPlan();renderAll();toast('Floor added',`${floorName({id})} added to the building graph. Connect rooms on this floor to its stair landing.`, 'success');}
  function addExtraStairConnection(){if(app.running){toast('Pause simulation','Change stair connections while the simulation is stopped.','error');return;}const next=app.currentFloor+1;if(!app.floors.some(f=>f.id===next)){toast('No floor above','Add another floor first, or select a lower floor.','error');return;}addStairConnection(app.currentFloor,next,520,300);renderAll();refreshPlan();toast('Stair connection added',`A new stair pair now connects ${floorName({id:app.currentFloor})} and ${floorName({id:next})}.`,'success');}
  function removeFloor(){if(app.running){toast('Pause simulation','Remove floors while the simulation is stopped.','error');return;}if(app.floors.length<=1)return;const id=app.currentFloor;if(!confirm(`Remove ${floorName({id})} and all rooms, exits, stair landings and links on it?`))return;const removed=new Set(app.nodes.filter(n=>n.floor===id).map(n=>n.id));app.nodes=app.nodes.filter(n=>n.floor!==id);app.edges=app.edges.filter(e=>!removed.has(e.a)&&!removed.has(e.b));app.floors=app.floors.filter(f=>f.id!==id).sort((a,b)=>a.id-b.id);const remap=new Map(app.floors.map((f,i)=>[f.id,i]));app.floors.forEach((f,i)=>{f.id=i;f.name=floorName(f);});app.nodes.forEach(n=>{if(remap.has(n.floor??0))n.floor=remap.get(n.floor??0);});app.currentFloor=Math.min(id,app.floors.length-1);app.remaining={};roomNodes().forEach(n=>app.remaining[n.id]=n.pop);app.selected=null;updateFloorControls();refreshPlan();renderAll();toast('Floor removed','The graph was updated and affected routes were recalculated.','success');}
  function nextRoomId(){for(let i=0;i<26;i++){const id=String.fromCharCode(65+i);if(!nodeById(id))return id;}let i=1;while(nodeById('ROOM'+i))i++;return 'ROOM'+i;}
  function addNode(type,x,y){const id=type==='exit'?(()=>{let i=1;while(nodeById('EXIT'+i))i++;return 'EXIT'+i;})():nextRoomId();const n={id,x:clamp(x,25,975),y:clamp(y,25,535),type,pop:type==='room'?20:0,capacity:25,floor:app.currentFloor};app.nodes.push(n);if(type==='room')app.remaining[id]=n.pop;selectElement('node',id);app.dirty=true;renderAll();logEvent('Building edited',`${type==='exit'?'Exit':'Room'} ${id} added.`);}
  function addEdge(a,b){if(a===b)return false;if(app.edges.some(e=>edgeKey(e.a,e.b)===edgeKey(a,b))){toast('Corridor exists',`${a} and ${b} are already connected.`,'error');return false;}const na=nodeById(a),nb=nodeById(b);if(na.floor!==nb.floor){toast('Different floors','Use Add stair connection to create a valid vertical link between floors.','error');return false;}app.edges.push({a,b,w:1,c:20,blocked:false,vertical:false});selectElement('edge',edgeKey(a,b));app.dirty=true;logEvent('Corridor added',`${a} ↔ ${b} · capacity 20 people/tick.`);renderAll();return true;}
  function selectElement(type,id){app.selected=type==='node'?{type:'node',id}:type==='edge'?{type:'edge',key:id}:null;renderInspector();draw();}
  canvas.addEventListener('pointerdown',ev=>{const p=canvasPoint(ev),n=hitNode(p);if(app.tool==='room'||app.tool==='exit'){const m=toModel(p.x,p.y);addNode(app.tool,m.x,m.y);return;}if(app.tool==='link'){if(n){if(!app.linkFrom){app.linkFrom=n.id;toast('Choose the second point',`Now click another node to connect to ${n.id}.`);draw();}else{if(addEdge(app.linkFrom,n.id))app.linkFrom=null;else if(app.linkFrom===n.id)toast('Choose another node','A corridor needs two different endpoints.','error');else app.linkFrom=n.id;}}return;}if(app.blockMode){const e=(n&&n.type==='stair'?app.edges.find(x=>x.vertical&&(x.a===n.id||x.b===n.id)):null)||hitEdge(p);if(e){e.blocked=!e.blocked;app.dirty=true;logEvent(e.blocked?'Corridor blocked':'Corridor reopened',`${e.a} ↔ ${e.b} ${e.blocked?'is now unavailable':'is available again'}.`,e.blocked?'danger':'info');refreshPlan();renderAll();toast(e.blocked?'Corridor blocked':'Corridor reopened',`${e.a} ↔ ${e.b}` ,e.blocked?'error':'success');}return;}if(n){selectElement('node',n.id);if(app.tool==='select'){app.drag={id:n.id,pointerId:ev.pointerId,dx:toModel(p.x,p.y).x-n.x,dy:toModel(p.x,p.y).y-n.y};canvas.setPointerCapture(ev.pointerId);}return;}const e=hitEdge(p);if(e){selectElement('edge',edgeKey(e.a,e.b));return;}app.selected=null;renderInspector();draw();});
  canvas.addEventListener('pointermove',ev=>{if(!app.drag)return;const p=canvasPoint(ev),m=toModel(p.x,p.y),n=nodeById(app.drag.id);if(n){n.x=clamp(m.x-app.drag.dx,20,980);n.y=clamp(m.y-app.drag.dy,20,540);if(n.type==='stair'){const ve=app.edges.find(e=>e.vertical&&(e.a===n.id||e.b===n.id));const paired=ve&&nodeById(ve.a===n.id?ve.b:ve.a);if(paired){paired.x=n.x;paired.y=n.y;}}draw();}});canvas.addEventListener('pointerup',()=>{if(app.drag){app.drag=null;renderAll();}});canvas.addEventListener('pointercancel',()=>{app.drag=null;});
  function renderInspector(){const empty=$('selectionEmpty'),form=$('selectionForm');if(!app.selected){empty.hidden=false;form.hidden=true;return;}empty.hidden=true;form.hidden=false;
    if(app.selected.type==='node'){const n=nodeById(app.selected.id);if(!n){app.selected=null;renderInspector();return;}const verticalEdge=n.type==='stair'?app.edges.find(e=>e.vertical&&(e.a===n.id||e.b===n.id)):null;form.innerHTML=`<div class="selection-form-title"><span>${escapeHtml(n.id)}</span><span class="type-badge">${n.type.toUpperCase()}</span></div>${n.type==='room'?`<div class="inspector-field"><label for="nodePop">Occupant count</label><input id="nodePop" type="number" min="0" max="10000" value="${n.pop}"></div>`:n.type==='exit'?`<div class="inspector-field"><label for="nodeCap">Exit capacity (people / tick)</label><input id="nodeCap" type="number" min="1" max="10000" value="${n.capacity||20}"></div>`:`<div class="inspector-field"><label>Vertical connection</label><input value="${escapeHtml(stairDestinationLabel(n))}" disabled></div>${verticalEdge?`<div class="field-pair"><div class="inspector-field"><label for="stairW">Travel time (min)</label><input id="stairW" type="number" min="0.1" step="0.1" value="${verticalEdge.w}"></div><div class="inspector-field"><label for="stairC">Capacity / tick</label><input id="stairC" type="number" min="1" value="${verticalEdge.c}"></div></div><label class="inline-check"><input type="checkbox" id="stairBlocked" ${verticalEdge.blocked?'checked':''}> Stair connection unavailable</label>`:'<div class="field-note">No vertical edge connected to this landing.</div>'}`}<div class="field-pair"><div class="inspector-field"><label for="nodeX">Map X</label><input id="nodeX" type="number" min="20" max="980" value="${Math.round(n.x)}"></div><div class="inspector-field"><label for="nodeY">Map Y</label><input id="nodeY" type="number" min="20" max="540" value="${Math.round(n.y)}"></div></div><div class="selection-buttons"><button class="btn btn-small btn-quiet" id="applyElement">Apply</button><button class="btn btn-small btn-danger" id="deleteElement">Delete</button></div>`;
      $('applyElement').onclick=()=>{if(n.type==='room')n.pop=clamp(+$('nodePop').value||0,0,10000);else if(n.type==='exit')n.capacity=clamp(+$('nodeCap').value||1,1,10000);else if(n.type==='stair'&&verticalEdge){verticalEdge.w=clamp(+$('stairW').value||1,.1,9999);verticalEdge.c=clamp(+$('stairC').value||1,1,10000);verticalEdge.blocked=$('stairBlocked').checked;}n.x=clamp(+$('nodeX').value||n.x,20,980);n.y=clamp(+$('nodeY').value||n.y,20,540);if(n.type==='stair'&&verticalEdge){const paired=nodeById(verticalEdge.a===n.id?verticalEdge.b:verticalEdge.a);if(paired){paired.x=n.x;paired.y=n.y;}}if(!app.running){app.remaining[n.id]=n.type==='room'?n.pop:0;}refreshPlan();renderAll();toast('Changes applied',`${n.id} updated and routes recalculated.`,'success');};
    }else{const e=edgeByKey(app.selected.key);if(!e){app.selected=null;renderInspector();return;}form.innerHTML=`<div class="selection-form-title"><span>${escapeHtml(e.a)} ↔ ${escapeHtml(e.b)}</span><span class="type-badge">${e.vertical?'STAIR LINK':'CORRIDOR'}</span></div><div class="field-pair"><div class="inspector-field"><label for="edgeW">${e.vertical?'Vertical travel time (min)':'Walk time (min)'}</label><input id="edgeW" type="number" min="0.1" step="0.1" value="${e.w}"></div><div class="inspector-field"><label for="edgeC">Capacity / tick</label><input id="edgeC" type="number" min="1" value="${e.c}"></div></div><label class="inline-check"><input type="checkbox" id="edgeBlocked" ${e.blocked?'checked':''}> ${e.vertical?'Stair connection unavailable':'Corridor blocked'}</label><div class="selection-buttons"><button class="btn btn-small btn-quiet" id="applyElement">Apply</button><button class="btn btn-small btn-danger" id="deleteElement">Delete</button></div>`;
      $('applyElement').onclick=()=>{e.w=clamp(+$('edgeW').value||1,.1,9999);e.c=clamp(+$('edgeC').value||1,1,10000);e.blocked=$('edgeBlocked').checked;refreshPlan();renderAll();toast('Corridor updated',`${e.a} ↔ ${e.b} settings applied.`,'success');};
    }
    $('deleteElement').onclick=()=>{if(app.selected.type==='node'){const id=n.id;app.nodes=app.nodes.filter(x=>x.id!==id);app.edges=app.edges.filter(x=>x.a!==id&&x.b!==id);delete app.remaining[id];}else app.edges=app.edges.filter(x=>edgeKey(x.a,x.b)!==e.key);app.selected=null;app.dirty=true;planRoutes();renderAll();toast('Element deleted','The building graph has been updated.','success');};
  }
  function renderAll(){updateFloorControls();resizeCanvas();renderInspector();updateStats();}

  function benchmark(){const strategies=[['fastest','Fastest route'],['balanced','Balanced cost'],['capacity','Capacity-first']];const out=[];strategies.forEach(([key,label])=>{const t0=performance.now();const routes={};roomNodes().forEach(n=>{if(n.pop>0){const r=routeFrom(n.id,key);if(r)routes[n.id]=r;}});const computeMs=performance.now()-t0;const stranded=roomNodes().filter(n=>n.pop>0&&!routes[n.id]).length;const duration=estimatedDuration(routes,Object.fromEntries(roomNodes().map(n=>[n.id,n.pop])));out.push({key,label,computeMs,duration,stranded,routes:Object.keys(routes).length,valid:stranded===0});});app.benchmark=out;renderBenchmark();toast('Benchmark complete',`${out.length} strategies evaluated against the current building.`,'success');}
  function renderBenchmark(){const rows=app.benchmark;if(!rows.length)return;$('benchStrategies').textContent=rows.length;$('benchBest').textContent=fmt(Math.min(...rows.map(r=>r.duration)))+' ticks';$('benchFastest').textContent=rows.slice().sort((a,b)=>a.computeMs-b.computeMs)[0].label;$('benchWhen').textContent=new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});const max=Math.max(1,...rows.map(r=>r.duration));$('comparisonChart').innerHTML='';rows.forEach(r=>{const row=document.createElement('div');row.className='chart-row';row.innerHTML=`<div class="chart-name">${escapeHtml(r.label)}<div class="chart-caption">${r.routes} routes · ${r.stranded} unreachable</div></div><div class="chart-bar-track"><div class="chart-bar" style="width:${Math.max(1,r.duration/max*100)}%"></div></div><div class="chart-value">${fmt(r.duration)} ticks</div>`;$('comparisonChart').appendChild(row);});$('benchTable').innerHTML=rows.map(r=>`<tr><td><b>${escapeHtml(r.label)}</b></td><td>${fmt(r.duration)} ticks</td><td>${r.computeMs.toFixed(3)} ms</td><td>${r.stranded}</td><td>${r.routes}</td><td class="${r.valid?'status-ok':'status-warn'}">${r.valid?'✓ Reachable':'⚠ Partial'}</td></tr>`).join('');}
  function downloadText(filename,text,type='text/plain'){const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function exportScenario(){const data={schemaVersion:3,exportedAt:new Date().toISOString(),title:'EvacuateLab multi-floor scenario',floors:app.floors,currentFloor:app.currentFloor,nodes:app.nodes,edges:app.edges,settings:{strategy:$('strategySelect').value,autoIncident:$('autoIncident').checked}};downloadText('evacuate-scenario.json',JSON.stringify(data,null,2),'application/json');toast('Scenario exported','JSON file includes nodes, corridors, capacities and blockages.','success');}
  function importScenario(data){if(!data||!Array.isArray(data.nodes)||!Array.isArray(data.edges))throw new Error('Invalid scenario file. Expected nodes and edges arrays.');const ids=new Set(data.nodes.map(n=>n.id));if(ids.size!==data.nodes.length||data.nodes.some(n=>!n.id||!['room','exit','stair'].includes(n.type))||data.edges.some(e=>!ids.has(e.a)||!ids.has(e.b)))throw new Error('Scenario contains invalid or duplicate node IDs or corridor references.');const floorsForCheck=Array.isArray(data.floors)&&data.floors.length?data.floors:[{id:0,name:'Ground Floor'}],floorIds=new Set(floorsForCheck.map(f=>+f.id)),nodeMapForCheck=new Map(data.nodes.map(n=>[n.id,n]));if(data.nodes.some(n=>!floorIds.has(Number.isInteger(+n.floor)?+n.floor:0)))throw new Error('Scenario contains a node assigned to a floor that does not exist.');if(data.edges.some(e=>{const a=nodeMapForCheck.get(e.a),b=nodeMapForCheck.get(e.b),fa=Number.isInteger(+a.floor)?+a.floor:0,fb=Number.isInteger(+b.floor)?+b.floor:0;return e.vertical?(!(a.type==='stair'&&b.type==='stair')||Math.abs(fa-fb)!==1):fa!==fb;}))throw new Error('Invalid floor link: corridors must stay on one floor; stair links must join stair landings on adjacent floors.');app.floors=Array.isArray(data.floors)&&data.floors.length?data.floors.map(f=>({id:+f.id,name:String(f.name||floorName({id:+f.id}))})): [{id:0,name:'Ground Floor'}];app.currentFloor=app.floors.some(f=>f.id===+(data.currentFloor??0))?+(data.currentFloor??0):app.floors[0].id;app.nodes=data.nodes.map(n=>({...n,x:clamp(+n.x||20,20,980),y:clamp(+n.y||20,20,540),pop:Math.max(0,+n.pop||0),capacity:Math.max(1,+n.capacity||20),floor:Number.isInteger(+n.floor)?+n.floor:0}));app.edges=data.edges.map(e=>({a:e.a,b:e.b,w:Math.max(.1,+e.w||1),c:Math.max(1,+e.c||20),blocked:!!e.blocked,vertical:!!e.vertical}));app.remaining={};roomNodes().forEach(n=>app.remaining[n.id]=n.pop);app.running=false;app.done=false;app.selected=null;app.particles=[];app.evacuated=0;app.tick=0;app.dirty=true;clearEvents();planRoutes();renderAll();logEvent('Scenario imported','Loaded a scenario JSON file.');toast('Import complete','Scenario loaded successfully.','success');}
  function saveCurrent(){const title=prompt('Name this scenario:',`Scenario ${app.saved.length+1}`);if(!title)return;app.saved.push({title,nodes:JSON.parse(JSON.stringify(app.nodes)),edges:JSON.parse(JSON.stringify(app.edges)),floors:JSON.parse(JSON.stringify(app.floors)),currentFloor:app.currentFloor,savedAt:new Date().toLocaleString()});renderSaved();toast('Scenario saved',`${title} is available in this session.`,'success');}
  function renderSaved(){const el=$('savedScenarios');if(!app.saved.length){el.innerHTML='<div class="empty-state compact"><b>No saved scenarios yet</b><span>Save the current building to return to it later.</span></div>';return;}el.innerHTML='';app.saved.forEach((s,i)=>{const row=document.createElement('div');row.className='saved-row';row.innerHTML=`<div class="saved-icon">◇</div><div><b>${escapeHtml(s.title)}</b><small>${s.floors?.length||1} floors · ${s.nodes.length} nodes · ${s.edges.length} links · ${escapeHtml(s.savedAt)}</small></div><div class="saved-spacer"></div><button data-load="${i}">Load</button><button data-delete="${i}">×</button>`;el.appendChild(row);});el.querySelectorAll('[data-load]').forEach(b=>b.onclick=()=>{const s=app.saved[+b.dataset.load];importScenario({nodes:s.nodes,edges:s.edges,floors:s.floors,currentFloor:s.currentFloor});navigate('planner');});el.querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>{app.saved.splice(+b.dataset.delete,1);renderSaved();});}
  function toast(title,message,type='info'){const el=document.createElement('div');el.className='toast '+type;el.innerHTML=`<b>${escapeHtml(title)}</b><span>${escapeHtml(message)}</span>`;$('toastStack').appendChild(el);setTimeout(()=>{el.style.opacity='0';el.style.transform='translateY(5px)';setTimeout(()=>el.remove(),250);},3400);}
  function navigate(view){document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===view));const map={planner:'plannerPage',analytics:'analyticsPage',scenarios:'scenariosPage'};$ (map[view]).classList.add('active');$('crumb').textContent=view==='planner'?'Command center':view==='analytics'?'Algorithm lab':'Scenario library';if(view==='planner')setTimeout(resizeCanvas,40);}

  $('tools').addEventListener('click',e=>{const b=e.target.closest('[data-tool]');if(!b)return;app.tool=b.dataset.tool;app.linkFrom=null;document.querySelectorAll('.tool[data-tool]').forEach(x=>x.classList.toggle('active',x===b));app.blockMode=false;$('blockModeBtn').classList.remove('active');canvas.style.cursor=app.tool==='select'?'grab':app.tool==='link'?'crosshair':'copy';$('canvasHint').textContent=app.tool==='link'?'Click two nodes to connect them.':app.tool==='room'?'Click the map to add a room.':app.tool==='exit'?'Click the map to add an exit.':'Select a corridor to inspect capacity · drag rooms to reposition';});
  $('blockModeBtn').onclick=()=>{app.blockMode=!app.blockMode;app.tool='select';document.querySelectorAll('.tool[data-tool]').forEach(x=>x.classList.toggle('active',x.dataset.tool==='select'));$('blockModeBtn').classList.toggle('active',app.blockMode);canvas.style.cursor=app.blockMode?'not-allowed':'grab';$('canvasHint').textContent=app.blockMode?'Click any corridor to toggle its blocked state.':'Select a corridor to inspect capacity · drag rooms to reposition';};
  document.querySelectorAll('.nav-item').forEach(b=>b.onclick=()=>navigate(b.dataset.view));
  $('runBtn').onclick=()=>{if(app.running){togglePause();return;}if(app.done||app.tick>0)startSimulation();else startSimulation();};$('pauseBtn').onclick=togglePause;$('applyBtn').onclick=()=>{refreshPlan();renderAll();logEvent('Plan refreshed','Routes and network metrics recalculated from the current graph.');toast('Plan refreshed','Routes recalculated using the current settings.','success');};
  $('strategySelect').onchange=()=>{refreshPlan();renderAll();if(app.running)logEvent('Routing policy changed',`Using ${$('strategySelect').selectedOptions[0].text}.`);};$('speedRange').oninput=()=>{$('speedValue').textContent=$('speedRange').value+'×';app.speed=+$('speedRange').value;};$('showLabels').onchange=draw;
  $('floorSelect').onchange=e=>{app.currentFloor=+e.target.value;app.selected=null;app.linkFrom=null;renderAll();draw();logEvent('Floor selected',`Viewing ${floorName(app.floors.find(f=>f.id===app.currentFloor)||{id:app.currentFloor})}.`);};$('addFloorBtn').onclick=addFloor;$('addStairLinkBtn').onclick=addExtraStairConnection;$('removeFloorBtn').onclick=removeFloor;
  $('sampleBtn').onclick=()=>sampleScenario('sample');$('resetViewBtn').onclick=()=>{app.zoom=1;app.panX=0;app.panY=0;resizeCanvas();};$('fitBtn').onclick=()=>{app.zoom=1;app.panX=0;app.panY=0;resizeCanvas();};$('zoomIn').onclick=()=>{app.zoom=clamp(app.zoom*1.15,.55,1.8);resizeCanvas();};$('zoomOut').onclick=()=>{app.zoom=clamp(app.zoom/1.15,.55,1.8);resizeCanvas();};$('exportBtn').onclick=exportScenario;$('importBtn').onclick=()=>$('scenarioFile').click();$('scenarioFile').onchange=e=>{const f=e.target.files[0];if(!f)return;const reader=new FileReader();reader.onload=()=>{try{importScenario(JSON.parse(reader.result));}catch(err){toast('Import failed',err.message,'error');}};reader.readAsText(f);e.target.value='';};$('benchmarkBtn').onclick=benchmark;$('downloadBenchBtn').onclick=()=>{if(!app.benchmark.length){toast('No benchmark data','Run the benchmark first.','error');return;}const header='strategy,estimated_model_duration_ticks,planner_time_ms,unreachable_rooms,routes_found,status';const rows=app.benchmark.map(r=>[r.label,r.duration,r.computeMs.toFixed(6),r.stranded,r.routes,r.valid?'reachable':'partial'].join(','));downloadText('evacuatelab-benchmark.csv',[header,...rows].join('\n'),'text/csv');};$('saveScenarioBtn').onclick=saveCurrent;document.querySelectorAll('[data-scenario]').forEach(b=>b.onclick=()=>{sampleScenario(b.dataset.scenario);navigate('planner');});
  $('helpBtn').onclick=()=>{$('helpModal').hidden=false;};$('closeHelp').onclick=()=>{$('helpModal').hidden=true;};$('helpModal').onclick=e=>{if(e.target===$('helpModal'))$('helpModal').hidden=true;};window.addEventListener('keydown',e=>{if(e.key==='Escape')$('helpModal').hidden=true;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='e'){e.preventDefault();exportScenario();}});
  $('canvasWrap').addEventListener('dragover',e=>{e.preventDefault();});$('canvasWrap').addEventListener('drop',e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(!f)return;const reader=new FileReader();reader.onload=()=>{try{importScenario(JSON.parse(reader.result));}catch(err){toast('Import failed',err.message,'error');}};reader.readAsText(f);});
  window.addEventListener('resize',resizeCanvas);
  function frame(now){if(!app.lastFrame)app.lastFrame=now;const dt=Math.min(100,now-app.lastFrame);app.lastFrame=now;if(app.running&&!app.paused){app.accumulator+=dt*app.speed/3;while(app.accumulator>=700&&app.running&&!app.paused){app.accumulator-=700;doTick();}}advanceParticles(dt);if(app.running&&!app.paused&&app.particles.length===0&&!roomNodes().some(n=>(app.remaining[n.id]||0)>0&&app.routes[n.id]))finishSimulation();draw();updateStats();requestAnimationFrame(frame);}

  // Small built-in self-checks make the demo safer to modify during the group project.
  function selfTest(){const checks=[];const add=(name,ok)=>checks.push({name,ok});add('sample has 9 rooms',roomNodes().length===9);add('sample has 2 exits',exitNodes().length===2);add('sample has one initial blockage',app.edges.filter(e=>e.blocked).length===1);const r=routeFrom('A','fastest');add('Dijkstra finds a route from A',!!r&&r.path[0]==='A'&&isExit(nodeById(r.path.at(-1))));add('blocked corridors excluded',!r?.edges.includes(edgeKey('C','D')));add('sample has positive total population',totalPopulation()>0);
    const oldNodes=app.nodes,oldEdges=app.edges,oldFloors=app.floors,oldFloor=app.currentFloor;
    app.floors=[{id:0,name:'Ground Floor'},{id:1,name:'Floor 2'}];app.currentFloor=1;
    app.nodes=[{id:'TEST_ROOM',type:'room',x:100,y:100,pop:1,floor:1},{id:'TEST_STAIR_UP',type:'stair',x:300,y:100,pop:0,floor:1},{id:'TEST_STAIR_GROUND',type:'stair',x:300,y:100,pop:0,floor:0},{id:'TEST_EXIT',type:'exit',x:500,y:100,pop:0,capacity:10,floor:0}];
    app.edges=[{a:'TEST_ROOM',b:'TEST_STAIR_UP',w:1,c:10,blocked:false,vertical:false},{a:'TEST_STAIR_UP',b:'TEST_STAIR_GROUND',w:2,c:10,blocked:false,vertical:true},{a:'TEST_STAIR_GROUND',b:'TEST_EXIT',w:1,c:10,blocked:false,vertical:false}];
    const crossFloor=routeFrom('TEST_ROOM','fastest');add('Dijkstra routes across a vertical stair link',!!crossFloor&&crossFloor.path.includes('TEST_STAIR_GROUND')&&crossFloor.path.at(-1)==='TEST_EXIT');
    app.nodes=oldNodes;app.edges=oldEdges;app.floors=oldFloors;app.currentFloor=oldFloor;return checks;}
  sampleScenario('sample');const checks=selfTest();console.info('[EvacuateLab self-check]',checks);if(checks.some(c=>!c.ok))toast('Self-check warning','One or more built-in checks failed. See the browser console.','error');requestAnimationFrame(frame);
})();
