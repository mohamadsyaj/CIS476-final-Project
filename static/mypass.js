function setupPasswordGenerator(){
  const btn = document.getElementById('generate-password');
  const pw = document.getElementById('password');
  if (!btn || !pw) return;
  btn.addEventListener('click', async (e)=>{
    e.preventDefault();
    const res = await fetch('/generate_password');
    const j = await res.json();
    if (j.password) { pw.value = j.password; }
  });
}

function setupTogglePassword(){
  document.querySelectorAll('button.toggle-password').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const target = document.getElementById(btn.dataset.target);
      if (!target) return;
      if (target.type === 'password'){ target.type = 'text'; btn.textContent='Hide'; }
      else { target.type='password'; btn.textContent='Show'; }
    })
  })
}

document.addEventListener('DOMContentLoaded', ()=>{
  setupPasswordGenerator(); setupTogglePassword();
});
// Central JS for MyPass: mediator UI, copy/unmask, auto-lock, auto-clear clipboard

const AUTO_LOCK_MS = 60 * 1000; // 1 minute
const CLIP_CLEAR_MS = 30 * 1000; // 30 seconds
let autoLockTimer = null;

function resetAutoLock() {
  if (autoLockTimer) clearTimeout(autoLockTimer);
  autoLockTimer = setTimeout(() => {
    // auto-logout
    window.location.href = '/logout';
  }, AUTO_LOCK_MS);
}

function setupAutoLock() {
  ['click','mousemove','keydown','scroll','touchstart'].forEach(ev => {
    window.addEventListener(ev, resetAutoLock, {passive:true});
  });
  resetAutoLock();
}

async function copyField(itemId, field) {
  const res = await fetch(`/vault/copy/${itemId}/${field}?action=copy`);
  const json = await res.json();
  if (json.value) {
    try {
      await navigator.clipboard.writeText(json.value);
      // schedule clearing
      setTimeout(async () => { try { await navigator.clipboard.writeText('') } catch(e){} }, CLIP_CLEAR_MS);
      return true;
    } catch(e){
      console.error('Clipboard write failed', e);
      return false;
    }
  }
  return false;
}

async function unmaskField(btn) {
  const id = btn.dataset.id;
  const field = btn.dataset.field;
  const row = btn.closest('tr');
  const valueCell = row.querySelector('.field-value');
  const maskedVal = valueCell.dataset.masked;
  // toggle behaviour
  if (btn.textContent.trim().toLowerCase() === 'unmask'){
    try {
      // request a short-lived unmask token from the server
      const tokenResp = await fetch(`/vault/request_unmask_token/${id}/${field}`, {method: 'POST'});
      const tokenJson = await tokenResp.json();
      if (!tokenResp.ok || !tokenJson.token) {
        alert(tokenJson.error || 'Unable to request unmask token');
        return;
      }
      const token = tokenJson.token;
      const res = await fetch(`/vault/copy/${id}/${field}?action=unmask&token=${encodeURIComponent(token)}`);
      const json = await res.json();
      if (json.value) {
        valueCell.textContent = json.value;
        btn.textContent = 'Mask';
        // set to clipboard as well for convenience
            try { 
              await navigator.clipboard.writeText(json.value);
              // schedule clearing clipboard after CLIP_CLEAR_MS
              setTimeout(async () => { try { await navigator.clipboard.writeText('') } catch(e){} }, CLIP_CLEAR_MS);
            } catch(e){}
        // auto re-mask after CLIP_CLEAR_MS as fallback
        setTimeout(()=>{
          if (btn.textContent.trim().toLowerCase() === 'mask'){
            valueCell.textContent = maskedVal;
            btn.textContent = 'Unmask';
          }
        }, CLIP_CLEAR_MS);
      } else {
        alert(json.error || 'Unable to unmask')
      }
    } catch(e) {
      console.error('unmask failed', e);
      alert('Unable to unmask');
    }
  } else {
    // mask
    valueCell.textContent = maskedVal;
    btn.textContent = 'Unmask';
  }
}

function initCopyUnmaskHandlers(){
  document.querySelectorAll('button.copy').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const id = btn.dataset.id;
      const field = btn.dataset.field;
      const ok = await copyField(id, field);
      if (ok) alert('Copied to clipboard — it will be cleared shortly');
      else alert('Unable to copy');
      if (ok){
        GLOBAL_MEDIATOR.notify('copyButton','copied',{id,field});
      }
    });
  });

  document.querySelectorAll('button.unmask').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const before = {id: btn.dataset.id, field: btn.dataset.field};
      await unmaskField(btn);
      GLOBAL_MEDIATOR.notify('unmaskButton','toggled', before);
    })
  });
}

// Lightweight mediator implementation for UI components
class UIMediatorJS {
  constructor(){
    this.components = {};
  }
  register(name, comp){ this.components[name] = comp; comp.mediator = this; }
  notify(senderName, event, payload){
    Object.keys(this.components).forEach(n => {
      if (n === senderName) return;
      try{ this.components[n].receive && this.components[n].receive(event, payload); }catch(e){}
    });
  }
}

function setupAddItemMediator(){
  const mediator = new UIMediatorJS();
  const select = document.querySelector('select[name="item_type"]');
  if (!select) return;
  const mapping = {
    'Login': ['username','password','url'],
    'CreditCard': ['card_number','cvv','expiry'],
    'Identity': ['ssn','passport','passport_expiry','license','license_expiry'],
    'SecureNote': ['notes']
  };

  const formComp = {
    receive(event, payload){
      if (event === 'typeChanged'){
        const type = payload;
        document.querySelectorAll('input,textarea').forEach(el => {
          const name = el.name;
          if (!name) return;
          if (name === 'title' || name === 'item_type') return;
          if (mapping[type] && mapping[type].includes(name)) {
            el.parentElement.style.display = '';
          } else {
            el.parentElement.style.display = 'none';
          }
        });
      }
    }
  };
  mediator.register('form', formComp);
  select.addEventListener('change', (e)=> mediator.notify('select','typeChanged', select.value));
  // initialize
  mediator.notify('select','typeChanged', select.value);
}

// Register global mediator for other components (password generator, clipboard)
const GLOBAL_MEDIATOR = new UIMediatorJS();

const PasswordGeneratorComponent = {
  receive(event, payload){
    if (event === 'generatePassword'){
      // payload: {length, upper, lower, digits, symbols, targetId}
      fetch(`/generate_password?length=${payload.length}&upper=${payload.upper?1:0}&lower=${payload.lower?1:0}&digits=${payload.digits?1:0}&symbols=${payload.symbols?1:0}`)
        .then(r => r.json())
        .then(j => {
          if (j.password && payload.targetId){
            const el = document.getElementById(payload.targetId);
            if (el){ el.value = j.password; el.dispatchEvent(new Event('input')); }
          }
        }).catch(()=>{});
    }
  }
};

const ClipboardComponent = {
  receive(event, payload){
    // centralize clipboard related UI events
    if (event === 'copied'){
      // payload: {id, field}
      try { window.dispatchEvent(new CustomEvent('mypass:copied', {detail: payload})); } catch(e){}
    }
  }
};

GLOBAL_MEDIATOR.register('pwdgen', PasswordGeneratorComponent);
GLOBAL_MEDIATOR.register('clipboard', ClipboardComponent);

// component to receive copy/unmask events and coordinate UI updates
const CopyUnmaskComponent = {
  receive(event, payload){
    if (event === 'copied'){
      // payload: {id, field}
      // could update per-row UI (e.g., flash) in future
    }
    if (event === 'unmasked'){
      // payload: {id, field, value}
      // central place to track unmask events
    }
  }
};
GLOBAL_MEDIATOR.register('copyUnmask', CopyUnmaskComponent);

function passwordIsWeak(pw){
  if (!pw) return true;
  if (pw.length < 8) return true;
  if (pw.toLowerCase() === pw) return true;
  if (!(/[0-9]/.test(pw))) return true;
  return false;
}

function updatePasswordHint(pw, hintId = 'password-hint'){
  const hint = document.getElementById(hintId);
  if (!hint) return;
  if (passwordIsWeak(pw)){
    hint.textContent = 'Warning: This password looks weak.';
    hint.style.color = 'crimson';
  } else {
    hint.textContent = 'Looks good.';
    hint.style.color = 'green';
  }
}

function setupPasswordGenerator(){
  const btn = document.getElementById('generate-password');
  const pwField = document.getElementById('password');
  if (!btn || !pwField) return;
  btn.addEventListener('click', async (e) => {
    e.preventDefault();
    try{
      const res = await fetch('/generate_password');
      const j = await res.json();
      if (j.password){
        pwField.value = j.password;
        updatePasswordHint(j.password);
        pwField.focus();
      }
    }catch(err){
      console.error('pwd gen failed', err);
      alert('Unable to generate password');
    }
  });

  pwField.addEventListener('input', (e)=>{
    updatePasswordHint(e.target.value);
  });
}

function setupRecoverPasswordGenerator(){
  const btn = document.getElementById('generate-password-recover');
  const pwField = document.getElementById('new_password');
  const hint = document.getElementById('recover-password-hint');
  if (!btn || !pwField) return;
  btn.addEventListener('click', async (e)=>{
    e.preventDefault();
    try{
      const res = await fetch('/generate_password');
      const j = await res.json();
      if (j.password){
        pwField.value = j.password;
        // update recover hint consistently using shared helper
        updatePasswordHint(j.password, 'recover-password-hint');
        pwField.focus();
      }
    }catch(err){
      console.error('pwd gen failed', err);
      alert('Unable to generate password');
    }
  });

  // live strength feedback while typing on recover page
  pwField.addEventListener('input', (e) => {
    updatePasswordHint(e.target.value, 'recover-password-hint');
  });
}

function setupTogglePasswordButtons(){
  document.querySelectorAll('button.toggle-password').forEach(btn => {
    btn.addEventListener('click', (e)=>{
      e.preventDefault();
      const targetId = btn.dataset.target;
      if (!targetId) return;
      const input = document.getElementById(targetId);
      if (!input) return;
      if (input.type === 'password'){
        input.type = 'text';
        btn.textContent = 'Hide';
        // optional: clear after delay
        setTimeout(()=>{
          if (input.type === 'text'){
            input.type = 'password';
            btn.textContent = 'Show';
          }
        }, CLIP_CLEAR_MS);
      } else {
        input.type = 'password';
        btn.textContent = 'Show';
      }
    });
  });
}

function init(){
  setupAutoLock();
  initCopyUnmaskHandlers();
  setupAddItemMediator();
  setupPasswordGenerator();
  setupRecoverPasswordGenerator();
  setupTogglePasswordButtons();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
