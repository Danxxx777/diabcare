/* ============================================================
   DiabCare - lógica de la pantalla de acceso
   Endpoints FastAPI reales: /api/auth/*
   ============================================================ */

const API_BASE = (() => {
  if (window.DiabCareNav && typeof DiabCareNav.getApi === "function") {
    return DiabCareNav.getApi();
  }
  const { protocol, hostname, port, origin } = window.location;
  if (port === "8000") return origin;
  const host = hostname && hostname !== "" ? hostname : "localhost";
  return `${protocol}//${host}:8000`;
})();

const EP = {
  login: "/api/auth/login",
  recuperar: "/api/auth/recuperar",
  resetear: "/api/auth/resetear",
  solicitud: "/api/auth/solicitud-acceso",
};

const HOME_DEFAULT = "/paginas/clinico/analisis/informes/index.html";

/* ---------- utilidades ---------- */
const $ = (sel) => document.querySelector(sel);

function detalleFastApi(cuerpo) {
  if (!cuerpo) return null;
  const d = cuerpo.detail ?? cuerpo.mensaje ?? cuerpo.message ?? cuerpo.error;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === "string" ? x : x.msg || JSON.stringify(x)))
      .filter(Boolean)
      .join(" - ");
  }
  return null;
}

function mostrarVista(id) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("view--on"));
  const v = document.getElementById(id);
  if (v) {
    v.classList.add("view--on");
    const primero = v.querySelector("input:not([hidden]), select:not([hidden])");
    if (primero && !primero.closest("[hidden]")) primero.focus();
  }
  document.querySelectorAll(".alert").forEach(ocultarAviso);

  if (id === "view-recuperar") {
    resetRecuperarPaso1();
    const emailLogin = $("#email")?.value?.trim();
    if (emailLogin) $("#email-rec").value = emailLogin;
  }
  if (id === "view-solicitud") {
    const emailLogin = $("#email")?.value?.trim();
    if (emailLogin) $("#email-sol").value = emailLogin;
  }
}

function aviso(el, texto, ok = false) {
  if (!el) return;
  const msg = String(texto || "").trim();
  if (!msg) {
    ocultarAviso(el);
    return;
  }
  el.textContent = msg;
  el.classList.toggle("alert--ok", ok);
  el.hidden = false;
}

function ocultarAviso(el) {
  el.hidden = true;
  el.textContent = "";
}

function cargando(btn, activo) {
  if (!btn) return;
  btn.classList.toggle("is-loading", activo);
  btn.disabled = activo;
}

function marcarInvalido(input, invalido) {
  if (!input) return;
  if (invalido) input.setAttribute("aria-invalid", "true");
  else input.removeAttribute("aria-invalid");
}

async function postJSON(ruta, datos) {
  const res = await fetch(API_BASE + ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(datos),
  });
  let cuerpo = null;
  try {
    cuerpo = await res.json();
  } catch (_) {
    /* sin JSON */
  }
  if (!res.ok) {
    throw new Error(detalleFastApi(cuerpo) || textoPorEstado(res.status));
  }
  return cuerpo || {};
}

function textoPorEstado(status) {
  if (status === 401 || status === 403) return "Correo o contraseña incorrectos.";
  if (status === 404) return "No encontramos una cuenta con ese correo.";
  if (status === 423) return "Tu cuenta está bloqueada. Contacta al administrador.";
  if (status === 429) return "Demasiados intentos. Espera un momento.";
  if (status >= 500) return "El servidor no responde. Intenta de nuevo.";
  return "No pudimos completar la operación.";
}

function homeParaRol(rol) {
  if (window.DiabCareNav && typeof DiabCareNav.homeParaRol === "function") {
    return DiabCareNav.homeParaRol(rol);
  }
  return HOME_DEFAULT;
}

async function redirigirSiSesionActiva() {
  try {
    if (sessionStorage.getItem("logout") === "1") return false;
    const res = await fetch(API_BASE + "/api/auth/sesion", {
      credentials: "include",
      cache: "no-store",
    });
    if (!res.ok) return false;
    const data = await res.json();
    if (!data.ok || !data.autenticado) return false;
    const u = data.usuario || {};
    sessionStorage.setItem("dc_sesion_ok", "1");
    sessionStorage.setItem("usuario", JSON.stringify(u));
    localStorage.removeItem("token");
    localStorage.setItem("usuario", JSON.stringify(u));
    if (u.debe_cambiar_password) {
      window.location.replace("/paginas/seguridad/perfil/index.html?forzar=1");
      return true;
    }
    window.location.replace(homeParaRol(u.rol));
    return true;
  } catch {
    return false;
  }
}

function t(key, fallback) {
  if (window.DiabCareI18n && typeof DiabCareI18n.t === "function") {
    const v = DiabCareI18n.t(key);
    if (v && v !== key) return v;
  }
  return fallback || key;
}

function aplicarI18nLogin() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (!key) return;
    el.textContent = t(key, el.textContent);
  });
  const idi = localStorage.getItem("diabcare_idioma") === "en" ? "en" : "es";
  document.documentElement.setAttribute("lang", idi);
  const lab = $("#idioma-lab");
  if (lab) lab.textContent = idi.toUpperCase();
  document.querySelectorAll("#menu-idioma [data-idi]").forEach((b) => {
    b.classList.toggle("is-on", b.dataset.idi === idi);
  });
  // Si estamos en paso 2 de recuperar, respetar lede2
  const paso2 = $("#rec-paso2");
  const lede = $("#rec-lede");
  if (lede && paso2 && !paso2.hidden) {
    lede.textContent = t("login_rec_lede2");
  }
}

function aplicarTemaLogin(tema) {
  const tma = tema === "claro" ? "claro" : "oscuro";
  document.documentElement.setAttribute("data-tema", tma);
  localStorage.setItem("diabcare_tema", tma);
  const title = tma === "oscuro" ? t("tb_tema_claro", "Cambiar a modo claro") : t("tb_tema_oscuro", "Cambiar a modo oscuro");
  const wrap = $("#btn-tema");
  if (wrap) wrap.title = title;
  const inp = wrap && wrap.querySelector ? wrap.querySelector(".dc-holo-input") : $("#holo-btn-tema");
  if (inp) {
    inp.checked = tma === "claro";
    inp.setAttribute("aria-label", title);
  }
}

function toggleTemaLogin(temaForzado) {
  const actual = document.documentElement.getAttribute("data-tema") === "claro" ? "claro" : "oscuro";
  const next = temaForzado === "claro" || temaForzado === "oscuro"
    ? temaForzado
    : (actual === "oscuro" ? "claro" : "oscuro");
  const root = document.documentElement;
  if (root.classList.contains("dc-theme-changing")) return;
  const btn = $("#btn-tema");
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const rect = btn?.getBoundingClientRect();
  if (rect) {
    root.style.setProperty("--dc-theme-x", `${rect.left + rect.width / 2}px`);
    root.style.setProperty("--dc-theme-y", `${rect.top + rect.height / 2}px`);
  }
  const aplicar = () => aplicarTemaLogin(next);
  root.classList.add("dc-theme-changing");
  if (!reduceMotion && typeof document.startViewTransition === "function") {
    document.startViewTransition(aplicar).finished.finally(() => {
      root.classList.remove("dc-theme-changing");
    });
    return;
  }
  aplicar();
  window.setTimeout(() => root.classList.remove("dc-theme-changing"), reduceMotion ? 0 : 480);
}

function setIdiomaLogin(cod) {
  const idi = cod === "en" ? "en" : "es";
  localStorage.setItem("diabcare_idioma", idi);
  document.documentElement.setAttribute("lang", idi);
  const menu = $("#menu-idioma");
  if (menu) menu.hidden = true;
  $("#btn-idioma")?.setAttribute("aria-expanded", "false");
  aplicarI18nLogin();
  aplicarTemaLogin(document.documentElement.getAttribute("data-tema"));
}

function wirePrefs() {
  if (window.DiabCareNav && typeof DiabCareNav.montarHolos === "function") {
    const btn = $("#btn-tema");
    if (btn && btn.classList.contains("toggle")) {
      const en = localStorage.getItem("diabcare_idioma") === "en";
      btn.classList.toggle("on", document.documentElement.getAttribute("data-tema") === "claro");
      DiabCareNav.montarHolos();
      const wrap = $("#btn-tema");
      const off = wrap && wrap.querySelector(".dc-holo-txt.off");
      const on = wrap && wrap.querySelector(".dc-holo-txt.on");
      if (off) off.textContent = en ? "DK" : "OS";
      if (on) on.textContent = en ? "LT" : "CL";
    }
  }
  const holo = document.querySelector("#btn-tema .dc-holo-input") || $("#holo-btn-tema");
  if (holo) {
    holo.addEventListener("change", (e) => {
      toggleTemaLogin(e.target.checked ? "claro" : "oscuro");
    });
  } else {
    $("#btn-tema")?.addEventListener("click", toggleTemaLogin);
  }
  const btnIdi = $("#btn-idioma");
  const menu = $("#menu-idioma");
  btnIdi?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (!menu) return;
    menu.hidden = !menu.hidden;
    btnIdi.setAttribute("aria-expanded", String(!menu.hidden));
  });
  menu?.querySelectorAll("[data-idi]").forEach((b) => {
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      setIdiomaLogin(b.dataset.idi);
    });
  });
  document.addEventListener("click", () => {
    if (menu && !menu.hidden) {
      menu.hidden = true;
      btnIdi?.setAttribute("aria-expanded", "false");
    }
  });
}

function nivelPassword(pwd) {
  const en = localStorage.getItem("diabcare_idioma") === "en";
  const p = String(pwd || "");
  if (!p) return { score: 0, label: t("login_pwd_hint", "Escribe una contraseña"), cls: "" };
  let score = 0;
  if (p.length >= 8) score += 1;
  if (p.length >= 12) score += 1;
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) score += 1;
  if (/\d/.test(p)) score += 1;
  if (/[^A-Za-z0-9]/.test(p)) score += 1;
  score = Math.min(4, score);
  const map = en
    ? {
        1: { label: "Weak", cls: "lvl-1" },
        2: { label: "Fair", cls: "lvl-2" },
        3: { label: "Good", cls: "lvl-3" },
        4: { label: "Strong", cls: "lvl-4" },
      }
    : {
        1: { label: "Débil", cls: "lvl-1" },
        2: { label: "Regular", cls: "lvl-2" },
        3: { label: "Buena", cls: "lvl-3" },
        4: { label: "Fuerte", cls: "lvl-4" },
      };
  if (p.length < 8) {
    return {
      score: 1,
      label: en ? "Too weak (min. 8)" : "Muy débil (mín. 8)",
      cls: "lvl-1",
    };
  }
  return { score, ...(map[score] || map[1]) };
}

function actualizarMedidorPwd(pwd) {
  const meter = $("#recPwdMeter");
  const label = $("#recPwdLabel");
  if (!meter || !label) return;
  const { score, label: txt, cls } = nivelPassword(pwd);
  meter.className = "pwd-meter" + (cls ? " " + cls : "");
  label.textContent = txt;
  meter.querySelectorAll(".pwd-meter-bars i").forEach((bar, i) => {
    bar.classList.toggle("on", i < score);
  });
}

function resetRecuperarPaso1() {
  const paso1 = $("#rec-paso1");
  const paso2 = $("#rec-paso2");
  const lede = $("#rec-lede");
  if (paso1) paso1.hidden = false;
  if (paso2) paso2.hidden = true;
  if (lede) lede.textContent = t("login_rec_lede");
  const codigo = $("#rec-codigo");
  const p1 = $("#rec-password");
  const p2 = $("#rec-password2");
  if (codigo) codigo.value = "";
  if (p1) p1.value = "";
  if (p2) p2.value = "";
  actualizarMedidorPwd("");
}

/* ---------- navegación entre vistas ---------- */
document.querySelectorAll("[data-goto]").forEach((b) => {
  b.addEventListener("click", () => mostrarVista(b.dataset.goto));
});

/* ---------- mostrar / ocultar contraseña ---------- */
function wireTogglePass(inputId, btnId) {
  const pass = document.getElementById(inputId);
  const ojo = document.getElementById(btnId);
  if (!pass || !ojo) return;
  ojo.addEventListener("click", () => {
    const visible = pass.type === "text";
    pass.type = visible ? "password" : "text";
    ojo.setAttribute("aria-pressed", String(!visible));
    ojo.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
    pass.focus();
  });
}
wireTogglePass("password", "toggle-pass");
wireTogglePass("rec-password", "toggle-rec-pass");
wireTogglePass("rec-password2", "toggle-rec-pass2");

/* ---------- aviso de Bloq Mayús ---------- */
const pass = $("#password");
const caps = $("#caps");
if (pass && caps) {
  pass.addEventListener("keyup", (e) => {
    if (typeof e.getModifierState === "function") {
      caps.hidden = !e.getModifierState("CapsLock");
    }
  });
  pass.addEventListener("blur", () => {
    caps.hidden = true;
  });
}

const recPwd = $("#rec-password");
if (recPwd) {
  recPwd.addEventListener("input", () => actualizarMedidorPwd(recPwd.value));
}

/* ---------- iniciar sesión ---------- */
const formLogin = $("#form-login");
const btnLogin = $("#submit-login");
const alertLogin = $("#alert-login");
const email = $("#email");

formLogin.addEventListener("submit", async (e) => {
  e.preventDefault();
  ocultarAviso(alertLogin);
  marcarInvalido(email, false);
  marcarInvalido(pass, false);

  if (!email.value.includes("@")) {
    marcarInvalido(email, true);
    aviso(alertLogin, "Escribe un correo válido.");
    return email.focus();
  }
  if (pass.value.length < 6) {
    marcarInvalido(pass, true);
    aviso(alertLogin, "La contraseña debe tener al menos 6 caracteres.");
    return pass.focus();
  }

  cargando(btnLogin, true);
  try {
    const data = await postJSON(EP.login, {
      email: email.value.trim().toLowerCase(),
      password: pass.value,
    });

    if (!data.usuario && !data.sesion_cookie) {
      throw new Error("Respuesta de login incompleta.");
    }

    // El JWT queda solo en cookie httpOnly; JS no lo guarda.
    localStorage.removeItem("token");
    sessionStorage.setItem("dc_sesion_ok", "1");
    sessionStorage.setItem("dc_entry_splash", "1");
    sessionStorage.setItem("usuario", JSON.stringify(data.usuario || {}));
    localStorage.setItem("usuario", JSON.stringify(data.usuario || {}));

    if (data.usuario && data.usuario.debe_cambiar_password) {
      window.location.replace("/paginas/seguridad/perfil/index.html?forzar=1");
      return;
    }

    const destino =
      data.redirect ||
      homeParaRol(data.usuario && data.usuario.rol) ||
      HOME_DEFAULT;
    window.location.replace(destino);
  } catch (err) {
    marcarInvalido(pass, true);
    aviso(alertLogin, err.message);
    pass.select();
  } finally {
    cargando(btnLogin, false);
  }
});

/* ---------- recuperar: paso 1 - enviar código ---------- */
const formRec = $("#form-recuperar");
formRec.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#submit-recuperar");
  const box = $("#alert-rec");
  ocultarAviso(box);
  const correo = $("#email-rec").value.trim().toLowerCase();
  if (!correo.includes("@")) {
    aviso(box, t("login_email_invalido", "Escribe un correo válido."));
    return $("#email-rec").focus();
  }

  cargando(btn, true);
  try {
    const data = await postJSON(EP.recuperar, { email: correo });
    const msg = data.mensaje || (localStorage.getItem("diabcare_idioma") === "en"
      ? "Done. Check your work email."
      : "Listo. Revisa tu correo institucional.");
    aviso(box, msg, true);
    $("#rec-paso1").hidden = true;
    $("#rec-paso2").hidden = false;
    const lede = $("#rec-lede");
    if (lede) lede.textContent = t("login_rec_lede2");
    $("#rec-codigo")?.focus();
  } catch (err) {
    aviso(box, err.message);
  } finally {
    cargando(btn, false);
  }
});

/* ---------- recuperar: paso 2 - resetear ---------- */
const formReset = $("#form-resetear");
formReset.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("#submit-resetear");
  const box = $("#alert-rec");
  ocultarAviso(box);

  const correo = $("#email-rec").value.trim().toLowerCase();
  const codigo = $("#rec-codigo").value.trim().toUpperCase();
  const password = $("#rec-password").value;
  const password2 = $("#rec-password2").value;
  const en = localStorage.getItem("diabcare_idioma") === "en";

  if (!codigo) {
    aviso(box, en ? "Enter the code from your email." : "Ingresa el código que llegó al correo.");
    return $("#rec-codigo").focus();
  }
  if (password.length < 8) {
    aviso(box, en ? "Password must be at least 8 characters." : "La contraseña debe tener al menos 8 caracteres.");
    return $("#rec-password").focus();
  }
  if (nivelPassword(password).score < 2) {
    aviso(box, en ? "Password is too weak. Use uppercase, numbers or symbols." : "La contraseña es muy débil. Usa mayúsculas, números o símbolos.");
    return $("#rec-password").focus();
  }
  if (password !== password2) {
    aviso(box, en ? "Passwords do not match." : "Las contraseñas no coinciden.");
    return $("#rec-password2").focus();
  }

  cargando(btn, true);
  try {
    const data = await postJSON(EP.resetear, {
      email: correo,
      codigo,
      password_nueva: password,
    });
    aviso(
      box,
      data.mensaje || (en ? "Password updated. You can sign in now." : "Contraseña actualizada. Ya puedes iniciar sesión."),
      true
    );
    if (email) email.value = correo;
    if (pass) pass.value = "";
    setTimeout(() => mostrarVista("view-login"), 1200);
  } catch (err) {
    aviso(box, err.message);
  } finally {
    cargando(btn, false);
  }
});

/* ---------- solicitud de acceso ---------- */
const formSol = $("#form-solicitud");
formSol.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = formSol.querySelector(".btn");
  const box = $("#alert-sol");
  ocultarAviso(box);
  const en = localStorage.getItem("diabcare_idioma") === "en";

  if (!$("#rol").value) {
    aviso(box, en ? "Select the role you need." : "Selecciona el rol que necesitas.");
    return $("#rol").focus();
  }

  const nombre = $("#nombre").value.trim();
  const correo = $("#email-sol").value.trim().toLowerCase();
  const cedula = $("#cedula").value.trim();
  const motivoExtra = $("#motivo")?.value?.trim() || "";
  const motivoParts = [];
  if (cedula) motivoParts.push(`Cédula: ${cedula}`);
  if (motivoExtra) motivoParts.push(motivoExtra);

  cargando(btn, true);
  try {
    const data = await postJSON(EP.solicitud, {
      nombre,
      email: correo,
      rol_solicitado: $("#rol").value,
      motivo: motivoParts.join(" - "),
    });
    aviso(
      box,
      data.mensaje || (en
        ? "Request sent. An administrator will contact you."
        : "Solicitud enviada. El administrador te contactará."),
      true
    );
    formSol.reset();
    if (email) email.value = correo;
    setTimeout(() => mostrarVista("view-login"), 2200);
  } catch (err) {
    aviso(box, err.message);
  } finally {
    cargando(btn, false);
  }
});

/* ---------- arranque ---------- */
async function init() {
  wirePrefs();

  if (sessionStorage.getItem("logout") === "1") {
    sessionStorage.removeItem("logout");
    sessionStorage.removeItem("dc_sesion_ok");
    sessionStorage.removeItem("usuario");
    const temaKeep = localStorage.getItem("diabcare_tema");
    const idiKeep = localStorage.getItem("diabcare_idioma");
    localStorage.clear();
    if (temaKeep) localStorage.setItem("diabcare_tema", temaKeep);
    if (idiKeep) localStorage.setItem("diabcare_idioma", idiKeep);
  }

  const guardado = localStorage.getItem("diabcare_tema");
  aplicarTemaLogin(guardado === "claro" ? "claro" : "oscuro");
  aplicarI18nLogin();

  if (await redirigirSiSesionActiva()) return;

  const sesionMsg = sessionStorage.getItem("sesion_msg");
  if (sesionMsg) {
    sessionStorage.removeItem("sesion_msg");
    aviso(alertLogin, sesionMsg);
  }

  email?.focus();
}

window.addEventListener("DOMContentLoaded", () => { init(); });
window.addEventListener("pageshow", () => { redirigirSiSesionActiva(); });
