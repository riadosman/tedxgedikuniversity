"use strict";

(() => {

  const app = document.getElementById("scanner-app");

  if (!app) return;

  const result = document.getElementById("scan-result"), video = document.getElementById("camera");

  const canvas = document.getElementById("scan-canvas"), context = canvas.getContext("2d", {willReadFrequently:true});

  const retry = document.getElementById("retry-scan");

  result.parentElement.prepend(result);

  const next = document.createElement("button"); next.type="button"; next.textContent=gettext("Next attendee"); next.hidden=true;

  result.after(next);

  const freshness = document.createElement("p"); freshness.className="muted";

  document.getElementById("scan-stats").after(freshness);

  let stream = null, busy = false, pending = null, pausedUntil = 0;

  let csrf = document.querySelector('[name="csrfmiddlewaretoken"]').value;

  const labels = {VALID:gettext("ADMIT — ticket accepted"),ALREADY_CHECKED_IN:gettext("DO NOT ADMIT AGAIN — already checked in"),INVALID:gettext("NOT VALID — ask the supervisor"),WRONG_EVENT:gettext("WRONG EVENT — ticket rejected"),REVOKED:gettext("REPLACED / REVOKED — use the latest ticket"),CANCELLED:gettext("CANCELLED — ticket rejected"),EXPIRED:gettext("EXPIRED — ask the supervisor"),ENTRY_PAUSED:gettext("ENTRY PAUSED — follow the supervisor’s instructions"),OUTSIDE_ENTRY_WINDOW:gettext("ENTRY CLOSED — outside admission hours")};

  function show(text, state) { result.textContent = text; result.className = "scan-result " + state; }

  function node(tag, text, className="") { const el=document.createElement(tag); el.textContent=text; el.className=className; return el; }

  async function send() {

    if (busy || !pending) return;

    busy=true; retry.hidden=true; show(gettext("Validating… Do not admit yet."), "");

    try {

      const response=await fetch(app.dataset.scanUrl, {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json","X-CSRFToken":csrf}, body:JSON.stringify(pending), signal:AbortSignal.timeout(5000)});

      if (!response.ok) throw new Error(gettext("The server could not confirm this request. Check sign-in and retry."));

      const data=await response.json();

      show((labels[data.code] || data.code.replaceAll("_"," ")) + (data.name ? " · " + data.name + " · " + data.ticket_type : ""), data.code === "VALID" ? "success" : "failure");

      pending=null; pausedUntil=Infinity; next.hidden=false;

      document.getElementById("credential").value="";

      await refresh().catch(()=>{freshness.textContent=gettext("Live counts unavailable — displayed totals may be stale. Check the connection.");});

    } catch (error) { show(gettext("OUTCOME UNKNOWN — do not admit. Restore the connection and retry this same request."),"uncertain"); retry.hidden=false; }

    finally { busy=false; }

  }

  function scan(credential) {

    if (busy || pending || Date.now()<pausedUntil) return;

    pending={request_id:crypto.randomUUID(),credential,device:document.getElementById("device").value}; send();

  }

  document.getElementById("scan-form").addEventListener("submit",event=>{event.preventDefault();scan(document.getElementById("credential").value.trim());});

  retry.addEventListener("click",async()=>{try{await refresh();await send();}catch{show(gettext("Sign in again in another tab if your session expired, then retry. Do not admit while the outcome is unknown."),"uncertain");}});

  next.addEventListener("click",()=>{if(!pending&&!busy){pausedUntil=0;next.hidden=true;show(gettext("Ready for the next attendee."),"");}});

  async function refresh(query="") {

    const response=await fetch(app.dataset.dataUrl+"?q="+encodeURIComponent(query),{credentials:"same-origin",signal:AbortSignal.timeout(8000)});

    if(!response.ok)throw new Error(gettext("Dashboard unavailable"));

    const data=await response.json(), stats=document.getElementById("scan-stats"); stats.replaceChildren();

    csrf=data.csrf_token;

    freshness.textContent=gettext("Live counts updated ")+new Date().toLocaleTimeString(document.documentElement.lang);

    [[gettext("Confirmed tickets"),data.registered],[gettext("Admitted"),data.checked_in],[gettext("Remaining"),data.remaining],[gettext("Entry mode"),(data.mode_label || data.mode)]].forEach(([label,value])=>{const card=node("div","","stat");card.append(node("span",label),node("strong",value));stats.append(card);});

    const recent=document.getElementById("recent-checkins"); recent.replaceChildren();

    data.recent.forEach(item=>recent.append(node("p",item.ticket__attendee__name+" · "+new Date(item.admitted_at).toLocaleTimeString(document.documentElement.lang),"list-item")));

    if(query){const matches=document.getElementById("lookup-results");matches.replaceChildren();

      if(!data.matches.length)matches.append(node("p",gettext("No attendee found. Refer to the supervisor."),"empty"));

      data.matches.forEach(item=>{const card=node("div","","list-item");card.append(node("strong",item.attendee__name),node("span",item.reference+" · "+item.ticket_type__name+(item.checkin__admitted_at?gettext(" · Already admitted")+" · "+new Date(item.checkin__admitted_at).toLocaleTimeString(document.documentElement.lang):"")));

        if(app.dataset.manual==="true"&&!item.checkin__admitted_at){const button=node("button",gettext("Manual check-in"),"secondary");button.type="button";button.addEventListener("click",()=>{if(busy||pending)return;const reason=window.prompt(gettext("Record the reason for manual admission:"));if(reason&&reason.trim()){pending={request_id:crypto.randomUUID(),ticket_id:item.id,reason,device:document.getElementById("device").value};send();}});card.append(button);}matches.append(card);});}

  }

  document.getElementById("lookup-form").addEventListener("submit",event=>{event.preventDefault();refresh(document.getElementById("lookup").value.trim()).catch(()=>show(gettext("Search unavailable. Check the connection."),"failure"));});

  function frame(){if(!stream)return;if(video.readyState>=2&&!busy&&!pending&&Date.now()>pausedUntil){canvas.width=video.videoWidth;canvas.height=video.videoHeight;context.drawImage(video,0,0);const pixels=context.getImageData(0,0,canvas.width,canvas.height);const code=window.jsQR?.(pixels.data,pixels.width,pixels.height,{inversionAttempts:"dontInvert"});if(code)scan(code.data);}setTimeout(frame,200);}

  document.getElementById("start-camera").addEventListener("click",async()=>{if(stream)return;try{if(!window.jsQR)throw new Error();stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:960}},audio:false});video.srcObject=stream;video.hidden=false;await video.play();frame();}catch(error){show(gettext("Camera unavailable. Allow camera access over HTTPS, use a USB scanner, or ask the supervisor for manual lookup."),"failure");}});

  document.getElementById("stop-camera").addEventListener("click",()=>{stream?.getTracks().forEach(track=>track.stop());stream=null;video.srcObject=null;video.hidden=true;});

  window.addEventListener("beforeunload",event=>{if(pending){event.preventDefault();event.returnValue=gettext("An admission request is unresolved.");}});

  refresh().catch(()=>show(gettext("Dashboard unavailable. Check your connection and sign-in."),"failure"));

  setInterval(()=>{if(!busy)refresh().catch(()=>{freshness.textContent=gettext("Live counts unavailable — displayed totals may be stale. Check the connection.");});},15000);

})();

