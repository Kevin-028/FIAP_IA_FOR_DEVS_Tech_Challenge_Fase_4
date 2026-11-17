/* Rosto do paciente em tempo real com MediaPipe Face Landmarker (roda no navegador).
   Estágio 1: a cada ~1 s envia ao servidor local só a média dos 52 blendshapes.
   Marca de atenção (ADR-004): toda suspeita de dor acima do nível 5 grava 2 s antes e 2 s depois
   (10 quadros por segundo) e aparece na hora para o médico.
   Estágio 2: o servidor põe cada marca na fila do validador e grava o veredito na própria marca;
   o navegador só envia o recorte (e o rosto neutro do início). O vídeo contínuo fica apenas na memória do
   navegador (últimos segundos) e é apagado ao desligar a câmera. A imagem nunca sai desta máquina. */
import { FaceLandmarker, FilesetResolver } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs";

const WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";
const MODELO = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const JANELA_MS = 1000;
const LADO_RECORTE = 256;
const MARGEM_RECORTE = 0.25;
const QUALIDADE_JPEG = 0.85;
const JANELA_NEUTRO = 3;   // recorte neutro na 3ª janela com rosto (calibração)

const consulta = window.consultaAoVivo;
const el = (id) => document.getElementById(id);
const raiz = document.getElementById("consulta-ao-vivo");

let landmarker = null;
let stream = null;
let ligada = false;
let ultimoTempo = -1;
let soma = {};
let quadros = 0;
let semRosto = 0;
let inicioJanela = 0;
let enviando = false;
let ultimoRosto = null;     // landmarks normalizados do último quadro com rosto
let janelasComRosto = 0;
let neutro = null;          // Blob JPEG em memória; descartado ao desligar
let estagio2 = true;
let ultimaEstimada = null;
// memória contínua: recortes do rosto a 10 por segundo, só os últimos segundos, nunca enviados inteiros.
// Um relógio próprio, separado da detecção facial: se o MediaPipe ficar lento (CPU), o recorte não perde quadros.
// marca: 2 s antes e 2 s depois do momento da suspeita (até 4 s, 40 quadros); marcas não se sobrepõem
const BUFFER_MS = 6500, PASSO_BUFFER_MS = 100, ANTES_MS = 2000, DEPOIS_MS = 2000, MAX_QUADROS_MARCA = 40;
let memoria = [];
let relogioDaMemoria = null;
let proximaMarca = 0;

async function capturarQuadro() {
  if (!ligada || !ultimoRosto) return;
  const agora = performance.now();
  const blob = await recortar();
  if (!blob || !ligada) return;
  memoria.push({ t: agora, blob });
  memoria = memoria.filter((q) => agora - q.t <= BUFFER_MS);
}

const avisarMarcas = () => document.dispatchEvent(new CustomEvent("marcas-de-atencao"));

async function gravarMarca(momento) {
  while (performance.now() < momento + DEPOIS_MS) await pausa(PASSO_BUFFER_MS);  // completa os 2 s depois
  await pausa(PASSO_BUFFER_MS);
  const trecho = memoria.filter((q) => q.t >= momento - ANTES_MS && q.t <= momento + DEPOIS_MS)
    .sort((a, b) => a.t - b.t).slice(-MAX_QUADROS_MARCA);
  if (trecho.length < 2) return null;
  const duracao = Math.min(4, Math.max(2, (trecho[trecho.length - 1].t - trecho[0].t + PASSO_BUFFER_MS) / 1000));
  const corpo = new FormData();
  corpo.append("duracao_s", duracao.toFixed(2));
  trecho.forEach((q, i) => corpo.append("quadros", q.blob, "q" + i + ".jpg"));
  if (neutro) corpo.append("neutro", neutro, "neutro.jpg");  // base do paciente para o validador
  try {
    const r = await fetch(consulta.api + "/duvidas", { method: "POST", body: corpo });
    return r.ok ? await r.json() : null;
  } catch (_) {
    return null;
  }
}

/* Suspeita acima do nível 5: grava o recorte e manda ao servidor; o servidor enfileira o validador
   e carimba o veredito na própria marca. A tela da consulta acompanha pela lista de marcas. */
async function marcarSuspeita() {
  const momento = performance.now();
  if (momento < proximaMarca) return;
  proximaMarca = momento + ANTES_MS + DEPOIS_MS;
  const marca = await gravarMarca(momento);
  if (!marca) {
    camStatus("Suspeita de dor sem recorte gravado (rosto fora da câmera?).");
    return;
  }
  if (estagio2) {
    el("cam-confirmacao").textContent = marca.na_fila > 1
      ? "validador: " + marca.na_fila + " marcas na fila"
      : "validador avaliando…";
  }
  avisarMarcas();  // recorte disponível para o médico, ainda "Avaliando…"
}

const tela = document.createElement("canvas");
tela.width = LADO_RECORTE;
tela.height = LADO_RECORTE;

const pausa = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function recortar() {
  const video = el("cam-video");
  if (!ultimoRosto || !video.videoWidth) return Promise.resolve(null);
  const xs = ultimoRosto.map((p) => p.x * video.videoWidth);
  const ys = ultimoRosto.map((p) => p.y * video.videoHeight);
  const largura = Math.max(...xs) - Math.min(...xs);
  const altura = Math.max(...ys) - Math.min(...ys);
  const lado = Math.min(Math.max(largura, altura) * (1 + 2 * MARGEM_RECORTE), video.videoWidth, video.videoHeight);
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2;
  const cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  const x = Math.min(Math.max(0, cx - lado / 2), video.videoWidth - lado);
  const y = Math.min(Math.max(0, cy - lado / 2), video.videoHeight - lado);
  tela.getContext("2d").drawImage(video, x, y, lado, lado, 0, 0, LADO_RECORTE, LADO_RECORTE);
  return new Promise((resolve) => tela.toBlob(resolve, "image/jpeg", QUALIDADE_JPEG));
}

function marcarFace(classe, valor) {
  for (const botao of document.querySelectorAll("#wong-baker .wb-face")) {
    botao.classList.toggle(classe, valor !== null && Number(botao.dataset.face) === valor);
  }
}

async function registrarAutorrelato(face) {
  try {
    const r = await fetch(consulta.api + "/autorrelato", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wong_baker: face }),
    });
    const dados = await r.json();
    if (!r.ok) {
      camStatus("Autorrelato recusado: " + (dados.error || r.status));
      return;
    }
    marcarFace("relatada", face);
    const estimado = dados.estimado === null ? "sem estimativa" : "câmera estimava " + dados.estimado;
    camStatus("Paciente apontou " + face + " (" + dados.descricao + "); " + estimado + ".");
  } catch (erro) {
    camStatus("Falha ao registrar autorrelato: " + erro);
  }
}

function camStatus(texto) {
  el("cam-status").textContent = texto;
}

function botao(ligar) {
  const b = el("btn-camera");
  if (b) b.textContent = ligar ? "Desligar câmera" : "Ligar câmera";
}

async function carregarModelo() {
  if (landmarker) return landmarker;
  camStatus("Carregando modelo facial…");
  const arquivos = await FilesetResolver.forVisionTasks(WASM);
  const opcoes = (delegate) => ({
    baseOptions: { modelAssetPath: MODELO, delegate },
    runningMode: "VIDEO",
    numFaces: 1,
    outputFaceBlendshapes: true,
  });
  try {
    landmarker = await FaceLandmarker.createFromOptions(arquivos, opcoes("GPU"));
  } catch (_) {
    landmarker = await FaceLandmarker.createFromOptions(arquivos, opcoes("CPU"));
  }
  return landmarker;
}

function pintarLeitura(leitura) {
  el("cam-expressao").textContent = leitura.expressao;
  el("cam-valencia").textContent = leitura.valencia;
  el("cam-dor").textContent = leitura.nivel_dor + " (+" + leitura.dor_relativa.toFixed(1) + " sobre a base)";
  if (leitura.wong_baker !== ultimaEstimada) {
    ultimaEstimada = leitura.wong_baker;
    marcarFace("estimada", leitura.wong_baker);
  }
  const barras = el("cam-barras");
  barras.replaceChildren();
  for (const [nome, valor] of Object.entries(leitura.scores)) {
    const linha = document.createElement("div");
    linha.className = "cam-barra";
    const rotulo = document.createElement("span");
    rotulo.textContent = nome;
    const trilho = document.createElement("span");
    trilho.className = "cam-trilho";
    const cheio = document.createElement("span");
    cheio.className = "cam-cheio" + (nome === "dor/desconforto" ? " dor" : "");
    cheio.style.width = Math.round(Math.min(1, valor) * 100) + "%";
    trilho.appendChild(cheio);
    linha.append(rotulo, trilho);
    barras.appendChild(linha);
  }
}

async function enviarJanela() {
  if (!quadros || enviando) return;
  const media = {};
  for (const [nome, total] of Object.entries(soma)) media[nome] = Math.round((total / quadros) * 1000) / 1000;
  soma = {};
  quadros = 0;
  enviando = true;
  try {
    const r = await fetch(consulta.api + "/face", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ blendshapes: media }),
    });
    const dados = await r.json();
    if (!r.ok) {
      camStatus("Servidor recusou a leitura: " + (dados.error || r.status));
      return;
    }
    pintarLeitura(dados.leitura);
    estagio2 = Boolean(dados.estagio2);
    camStatus("Analisando o rosto ao vivo. Cada suspeita de dor acima do nível 5 grava 2 s antes e 2 s depois para sua revisão"
      + (estagio2 ? "; o validador opina em seguida." : " (validador não instalado)."));
    if (dados.eventos_novos.length || dados.alerta_dor) consulta.carregar();
    janelasComRosto += 1;
    if (estagio2 && !neutro && janelasComRosto === JANELA_NEUTRO) neutro = await recortar();
    if (dados.suspeita) marcarSuspeita();
  } catch (erro) {
    camStatus("Falha ao enviar leitura: " + erro);
  } finally {
    enviando = false;
  }
}

function quadro() {
  if (!ligada) return;
  const video = el("cam-video");
  if (video.readyState >= 2 && video.currentTime !== ultimoTempo) {
    ultimoTempo = video.currentTime;
    const resultado = landmarker.detectForVideo(video, performance.now());
    const categorias = resultado.faceBlendshapes && resultado.faceBlendshapes[0];
    if (categorias) {
      semRosto = 0;
      ultimoRosto = resultado.faceLandmarks && resultado.faceLandmarks[0];  // o relógio da memória recorta aqui
      for (const c of categorias.categories) soma[c.categoryName] = (soma[c.categoryName] || 0) + c.score;
      quadros += 1;
    } else if (++semRosto === 1) {
      ultimoRosto = null;
    } else if (semRosto === 30) {
      camStatus("Rosto não encontrado. Centralize o paciente na câmera.");
    }
  }
  const agora = performance.now();
  if (agora - inicioJanela >= JANELA_MS) {
    inicioJanela = agora;
    enviarJanela();
  }
  requestAnimationFrame(quadro);
}

async function ligar() {
  if (ligada) return;
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error(consulta.explicarDispositivo({ name: "SecurityError" }, "câmera"));
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false });
  } catch (erro) {
    const texto = consulta.explicarDispositivo(erro, "câmera");
    camStatus(texto);
    throw new Error(texto);
  }
  const video = el("cam-video");
  video.srcObject = stream;
  await video.play();
  el("cam-off").classList.add("d-none");
  try {
    await carregarModelo();
  } catch (erro) {
    desligar();
    const texto = "Modelo facial não carregou (sem internet?): " + (erro.message || erro);
    camStatus(texto);
    throw new Error(texto);
  }
  ligada = true;
  botao(true);
  relogioDaMemoria = setInterval(capturarQuadro, PASSO_BUFFER_MS);
  inicioJanela = performance.now();
  camStatus("Calibrando com o rosto neutro do paciente (primeiros segundos)…");
  requestAnimationFrame(quadro);
}

function desligar() {
  ligada = false;
  clearInterval(relogioDaMemoria);
  relogioDaMemoria = null;
  if (stream) stream.getTracks().forEach((track) => track.stop());
  stream = null;
  const video = el("cam-video");
  if (video) video.srcObject = null;
  el("cam-off")?.classList.remove("d-none");
  botao(false);
  soma = {};
  quadros = 0;
  ultimoRosto = null;
  neutro = null;
  memoria = [];  // o vídeo contínuo é apagado; ficam só os recortes das marcas
  proximaMarca = 0;
  janelasComRosto = 0;
  camStatus("Câmera desligada. Só os recortes das marcas de atenção ficaram gravados.");
}

window.addEventListener("pagehide", () => { if (ligada) desligar(); });

window.cameraFacial = { ligar, desligar };

if (raiz && raiz.dataset.ativa === "sim" && el("btn-camera")) {
  el("btn-camera").addEventListener("click", async () => {
    if (ligada) {
      desligar();
      return;
    }
    try { await ligar(); } catch (_) { /* mensagem já exibida */ }
  });
  for (const botao of document.querySelectorAll("#wong-baker button.wb-face")) {
    botao.addEventListener("click", () => registrarAutorrelato(Number(botao.dataset.face)));
  }
}
