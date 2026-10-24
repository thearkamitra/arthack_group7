/* Live Unity preview and mock head direction. Provider credentials stay on Mac. */
(function () {
  let sid=null, state=null, busy=false, previewAt=0;
  let speechSequence=Date.now()*1000;
  async function request(id,path,body) {
    const response=await fetch(`/api/sessions/${id}/demo/${path}`,{credentials:'same-origin',method:body?'POST':'GET',headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
    const value=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(value.detail||'Unity demo unavailable');return value;
  }
  const api={
    get state(){return state;},
    async start(id){await window.LandscapeBackend.flush();const response=await fetch(`/api/sessions/${id}`,{credentials:'same-origin'});if(!response.ok)throw new Error('Session unavailable');const session=await response.json();if(!session.media?.url)await window.LandscapeBackend.canonical(id);sid=id;state=await request(id,'start',{});await poll();},
    async move(action){if(!sid||!state?.connected||state.headset||state.busy)return;state=await request(sid,'input',{action});},
    async speech(id,speaking,window_id){return request(id,'speech',{speaking,window_id,sequence:++speechSequence});},
  };
  async function poll(){
    if(busy)return;
    const panel=document.querySelector('[data-demo-session]');
    if(!panel||document.hidden){sid=null;return;}
    sid=panel.dataset.demoSession;
    busy=true;
    try{
      const response=await fetch(`/api/sessions/${sid}`,{credentials:'same-origin'});if(!response.ok)throw new Error('Coordinator unavailable');
      const session=await response.json();state=session.demo;
      if(session.status!=='active'&&window.LandscapeVoice?.active)await window.LandscapeVoice.stop();
      const slot=document.querySelector('#scene-slot');if(!slot)return;
      let view=document.querySelector('#unity-demo-panel');
      if(!state?.enabled){view?.remove();const old=slot.querySelector('#scene');if(old)old.hidden=false;return;}
      if(!view){
        view=document.createElement('div');view.id='unity-demo-panel';
        view.innerHTML='<div class="unity-live"><img id="unity-demo-frame" alt="Live Unity camera preview"><span class="unity-reticle" aria-hidden="true">+</span></div><p id="unity-demo-status" role="status"></p><div class="unity-arrows" aria-label="Mock head direction"><button type="button" data-camera="up" aria-label="Look up">↑</button><div><button type="button" data-camera="left" aria-label="Look left">←</button><button type="button" data-camera="center">Center</button><button type="button" data-camera="right" aria-label="Look right">→</button></div><button type="button" data-camera="down" aria-label="Look down">↓</button><button type="button" data-camera="freeze">Confirm most-looked region</button></div>';
        slot.prepend(view);
      }
      const headset=state.headset;const old=slot.querySelector('#scene');if(old)old.hidden=!headset;
      view.querySelector('.unity-live').hidden=headset;
      const image=view.querySelector('img');
      image.hidden=!state.frame_ready;
      if(state.frame_ready&&Date.now()-previewAt>350){previewAt=Date.now();image.src=`/api/sessions/${sid}/demo/frame?t=${previewAt}`;}
      document.querySelector('#unity-demo-status').textContent=headset?'Headset connected · browser arrows disabled':!state.connected?'Waiting for Unity Editor. Open this project; save any unsaved scene changes.':'LIVE UNITY DEMO · arrows simulate head direction · '+(state.busy?'transition in progress':`${state.yaw}° horizontal / ${-state.pitch}° vertical${session.spatialDecision ? " · Region confirmed: cell " + (session.spatialDecision.cell + 1) : ""}`);
      view.querySelectorAll('[data-camera]').forEach(b=>b.disabled=!state.connected||headset||state.busy||session.status!=='active'||session.pendingCycle);
    }catch(error){const label=document.querySelector('#unity-demo-status');if(label)label.textContent=error.message;state=null;document.querySelectorAll('[data-camera]').forEach(b=>b.disabled=true);}
    finally{busy=false;}
  }
  document.addEventListener('click',event=>{const button=event.target.closest('[data-camera]');if(button&&!button.disabled)api.move(button.dataset.camera).catch(e=>{document.querySelector('#unity-demo-status').textContent=e.message;});});
  document.addEventListener('keydown',event=>{
    if(event.target.closest('input,textarea,select,[contenteditable="true"]')||!document.querySelector('#unity-demo-panel'))return;
    const action={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right'}[event.key];
    if(action){event.preventDefault();api.move(action).catch(()=>{});}
  });
  setInterval(poll,250);
  window.LandscapeDemo=api;
})();
