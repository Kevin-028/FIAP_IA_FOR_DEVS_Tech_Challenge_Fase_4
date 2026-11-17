/* Consulta ao vivo: conversa transcrita pelo Azure Speech, papéis deduzidos no servidor,
   pontos de atenção marcados no texto e eventos do rosto do paciente na linha do tempo. */
(() => {
  const raiz = document.getElementById("consulta-ao-vivo");
  if (!raiz) return;
  const sessao = raiz.dataset.sessao;
  const ativa = raiz.dataset.ativa === "sim";
  const api = "/api/sessoes/" + encodeURIComponent(sessao);
  const NOMES = { medico: "Médico", paciente: "Paciente", acompanhante: "Acompanhante" };
  const el = (id) => document.getElementById(id);
  let estado = { falas: [], pontos: [], locutores: {}, locutores_detalhe: {}, eventos_face: [] };
  let transcriber = null;
  let renovarToken = null;

  function status(texto, gravando) {
    const alvo = el("live-status");
    alvo.replaceChildren();
    if (gravando) {
      const dot = document.createElement("span");
      dot.className = "live-rec-dot";
      alvo.appendChild(dot);
    }
    alvo.appendChild(document.createTextNode(texto));
  }

  function explicarDispositivo(erro, dispositivo) {
    const nome = (erro && erro.name) || "";
    const Disp = dispositivo.charAt(0).toUpperCase() + dispositivo.slice(1);
    if (!window.isSecureContext) {
      return "O navegador só libera " + dispositivo + " em https ou em http://localhost / http://127.0.0.1.";
    }
    if (nome === "NotAllowedError" || nome === "SecurityError") {
      return Disp + " bloqueado(a). Clique no ícone à esquerda do endereço → " + Disp + " → Permitir e recarregue. "
        + "No Windows: Configurações → Privacidade e segurança → " + Disp + " → ative o acesso, inclusive para aplicativos da área de trabalho. "
        + "Se o navegador embutido bloquear o " + dispositivo + ", use o Chrome ou o Edge.";
    }
    if (nome === "NotFoundError" || nome === "OverconstrainedError") return "Nenhum(a) " + dispositivo + " encontrado(a).";
    if (nome === "NotReadableError") return Disp + " em uso por outro aplicativo (Teams, Zoom…). Feche-o e tente de novo.";
    return "Falha ao abrir " + dispositivo + ": " + (erro && erro.message ? erro.message : erro);
  }

  function nomeLocutor(locutor) {
    if (!locutor || locutor === "Unknown") return "Identificando voz…";
    if (locutor.startsWith("digitado-")) return "Digitado";
    return locutor.replace("Guest-", "Voz ");
  }

  function rotulo(locutor) {
    const info = estado.locutores_detalhe[locutor];
    if (!info) return nomeLocutor(locutor);
    const auto = info.origem === "auto" ? " · auto " + Math.round((info.confianca || 0.5) * 100) + "%" : "";
    return NOMES[info.papel] + auto;
  }

  function hora(iso) {
    return (iso || "").substring(11, 19);
  }

  // Classe CSS por tipo de entidade (cores na legenda do Resumo clínico).
  const CLASSE_TIPO = {
    "Medicamento": "med", "Dose / posologia": "dose", "Alergia": "alergia", "Doença / condição": "doenca",
    "Sintoma": "sintoma", "Parte do corpo": "corpo", "Tempo / evolução": "tempo", "Medida relatada": "medida",
    "Exame": "exame", "Histórico familiar": "familia", "Cirurgia / procedimento": "cirurgia", "Hábito": "habito",
  };
  const classeTipo = (tipo) => "ent-" + (CLASSE_TIPO[tipo] || "outro");

  // Pontos de atenção viram <mark>; medicamentos, doenças etc. viram sublinhado colorido onde não há marca.
  function textoComMarcas(texto, pontos, entidades) {
    const frag = document.createDocumentFragment();
    const faixas = [];
    const sobrepoe = (ini, fim) => faixas.some((f) => ini < f.fim && fim > f.ini);
    const minusculo = texto.toLowerCase();
    for (const ponto of pontos) {
      if (ponto.origem !== "regra") continue;
      const i = minusculo.indexOf(ponto.trecho.toLowerCase());
      if (i < 0 || sobrepoe(i, i + ponto.trecho.length)) continue;
      faixas.push({ ini: i, fim: i + ponto.trecho.length, ponto });
    }
    for (const ent of entidades || []) {
      if (!sobrepoe(ent.inicio, ent.fim)) faixas.push({ ini: ent.inicio, fim: ent.fim, ent });
    }
    faixas.sort((a, b) => a.ini - b.ini);
    let pos = 0;
    for (const f of faixas) {
      frag.appendChild(document.createTextNode(texto.slice(pos, f.ini)));
      let alvo;
      if (f.ponto) {
        alvo = document.createElement("mark");
        alvo.className = f.ponto.severidade;
        alvo.title = f.ponto.categoria + ": " + f.ponto.motivo;
      } else {
        alvo = document.createElement("span");
        alvo.className = "ent " + classeTipo(f.ent.tipo) + (f.ent.negada ? " ent-neg" : "");
        alvo.title = f.ent.tipo + (f.ent.negada ? " (negado)" : "");
      }
      alvo.textContent = texto.slice(f.ini, f.fim);
      frag.appendChild(alvo);
      pos = f.fim;
    }
    frag.appendChild(document.createTextNode(texto.slice(pos)));
    return frag;
  }

  function irParaFala(ordem) {
    const fala = estado.falas.find((f) => f.ordem === ordem);
    const alvo = fala && el("fala-" + fala.id);
    if (!alvo) return;
    alvo.scrollIntoView({ behavior: "smooth", block: "center" });
    alvo.classList.add("flash");
    setTimeout(() => alvo.classList.remove("flash"), 1500);
  }

  function pintarResumo(grupos) {
    const caixa = el("resumo-clinico");
    if (!caixa) return;
    caixa.replaceChildren();
    const total = (grupos || []).reduce((n, g) => n + g.itens.length, 0);
    el("resumo-total").textContent = total;
    if (!total) {
      const vazio = document.createElement("p");
      vazio.className = "text-muted small mb-0";
      vazio.textContent = "Medicamentos, doenças, exames, doses e hábitos citados aparecem aqui.";
      caixa.appendChild(vazio);
      return;
    }
    for (const grupo of grupos) {
      const linha = document.createElement("div");
      linha.className = "resumo-grupo";
      const titulo = document.createElement("div");
      titulo.className = "resumo-tipo " + classeTipo(grupo.tipo);
      titulo.textContent = grupo.tipo;
      const chips = document.createElement("div");
      chips.className = "resumo-chips";
      for (const item of grupo.itens) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "resumo-chip " + classeTipo(grupo.tipo) + (item.negada ? " ent-neg" : "");
        chip.textContent = (item.negada ? "não: " : "") + item.texto + (item.vezes > 1 ? " ×" + item.vezes : "");
        if (item.medico) {
          const tag = document.createElement("small");
          tag.className = "resumo-medico";
          tag.textContent = "médico";
          chip.appendChild(tag);
        }
        chip.title = (item.negada ? "Negado. " : "") + (item.medico ? "Dito pelo médico. " : "")
          + "Fala " + item.falas.join(", ") + " — clique para ver na conversa.";
        chip.onclick = () => irParaFala(item.falas[item.falas.length - 1]);
        chips.appendChild(chip);
      }
      linha.append(titulo, chips);
      caixa.appendChild(linha);
    }
  }

  function pintarLocutores() {
    const caixa = el("locutores");
    caixa.replaceChildren();
    const vozes = [...new Set(estado.falas.map((f) => f.locutor))]
      .filter((l) => l && l !== "Unknown" && !l.startsWith("digitado-"));
    if (!vozes.length) return;
    const titulo = document.createElement("span");
    titulo.className = "text-muted";
    titulo.textContent = "Vozes:";
    caixa.appendChild(titulo);
    for (const locutor of vozes) {
      const info = estado.locutores_detalhe[locutor];
      const grupo = document.createElement("label");
      grupo.className = "chat-voz";
      grupo.title = info && info.origem === "auto"
        ? "Papel deduzido pelo jeito de falar. Mude se estiver errado."
        : (info ? "Definido por você" : "Ainda identificando");
      grupo.appendChild(document.createTextNode(nomeLocutor(locutor) + " →"));
      const select = document.createElement("select");
      select.className = "campo-sm";
      select.appendChild(new Option(info ? "—" : "identificando…", ""));
      for (const [valor, nome] of Object.entries(NOMES)) select.appendChild(new Option(nome, valor));
      select.value = info ? info.papel : "";
      select.disabled = !ativa;
      select.onchange = async () => {
        if (!select.value) return;
        const r = await fetch(api + "/locutores", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ locutor, papel: select.value }),
        });
        if (r.ok) pintarConversa(await r.json());
      };
      grupo.appendChild(select);
      if (info && info.origem === "auto") {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = "auto " + Math.round((info.confianca || 0.5) * 100) + "%";
        grupo.appendChild(chip);
      }
      caixa.appendChild(grupo);
    }
  }

  function balao(fala, pontos) {
    const papel = estado.locutores[fala.locutor] || "indefinido";
    const linha = document.createElement("div");
    linha.className = "chat-linha chat-" + papel;
    const bolha = document.createElement("div");
    bolha.className = "chat-bolha" + (pontos.length ? " tem-ponto" : "");
    bolha.id = "fala-" + fala.id;
    const meta = document.createElement("div");
    meta.className = "live-fala-meta";
    const extras = [hora(fala.criado_em)];
    if (fala.sentimento) extras.push("fala " + fala.sentimento);
    meta.textContent = rotulo(fala.locutor) + " · " + extras.join(" · ");
    const texto = document.createElement("div");
    texto.appendChild(textoComMarcas(fala.texto, pontos, fala.entidades));
    bolha.append(meta, texto);
    if (fala.expressao_face && fala.expressao_face !== "neutra" && papel !== "medico") {
      const rosto = document.createElement("div");
      rosto.className = "chat-rosto";
      rosto.textContent = "rosto: " + fala.expressao_face;
      bolha.appendChild(rosto);
    }
    linha.appendChild(bolha);
    return linha;
  }

  function eventoRosto(evento) {
    const linha = document.createElement("div");
    linha.className = "chat-evento" + (evento.tipo === "dor" ? " dor" : "");
    linha.textContent = evento.descricao + " · " + hora(evento.registrado_em);
    return linha;
  }

  function pintarConversa(dados) {
    estado = dados;
    const caixa = el("transcript");
    const noFim = caixa.scrollTop + caixa.clientHeight >= caixa.scrollHeight - 30;
    caixa.replaceChildren();
    const linhaDoTempo = [
      ...dados.falas.map((f) => ({ quando: f.criado_em, ordem: 0, item: f, tipo: "fala" })),
      ...(dados.eventos_face || []).map((e) => ({ quando: e.registrado_em, ordem: 1, item: e, tipo: "rosto" })),
    ].sort((a, b) => (a.quando < b.quando ? -1 : a.quando > b.quando ? 1 : a.ordem - b.ordem));
    if (!linhaDoTempo.length) {
      const vazio = document.createElement("p");
      vazio.className = "text-muted mb-0";
      vazio.textContent = "A conversa aparece aqui assim que você iniciar a consulta ao vivo.";
      caixa.appendChild(vazio);
    }
    for (const entrada of linhaDoTempo) {
      if (entrada.tipo === "fala") {
        caixa.appendChild(balao(entrada.item, dados.pontos.filter((p) => p.fala_id === entrada.item.id)));
      } else {
        caixa.appendChild(eventoRosto(entrada.item));
      }
    }
    if (noFim) caixa.scrollTop = caixa.scrollHeight;

    const lista = el("pontos");
    lista.replaceChildren();
    el("pontos-total").textContent = dados.pontos.length;
    if (!dados.pontos.length) {
      const vazio = document.createElement("li");
      vazio.className = "lista-vazia";
      vazio.textContent = "Nenhum ponto marcado ainda.";
      lista.appendChild(vazio);
    }
    for (const ponto of dados.pontos) {
      const item = document.createElement("li");
      item.className = "ponto " + ponto.severidade;
      const cabeca = document.createElement("div");
      cabeca.className = "forte";
      cabeca.textContent = ponto.categoria + (ponto.severidade === "alta" ? " · alta" : "");
      const trecho = document.createElement("div");
      trecho.className = "small";
      trecho.textContent = "“" + ponto.trecho + "”";
      const motivo = document.createElement("div");
      motivo.className = "small text-muted";
      motivo.textContent = ponto.motivo + " · fala " + ponto.ordem + (ponto.origem === "azure" ? " · Azure" : "");
      item.append(cabeca, trecho, motivo);
      item.onclick = () => {
        const alvo = el("fala-" + ponto.fala_id);
        if (!alvo) return;
        alvo.scrollIntoView({ behavior: "smooth", block: "center" });
        alvo.classList.add("flash");
        setTimeout(() => alvo.classList.remove("flash"), 1500);
      };
      lista.appendChild(item);
    }
    pintarLocutores();
    pintarResumo(dados.resumo_clinico);
  }

  async function carregar() {
    const r = await fetch(api + "/transcricao");
    if (r.ok) pintarConversa(await r.json());
  }

  async function enviarFala(corpo) {
    const r = await fetch(api + "/falas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    });
    const dados = await r.json();
    if (!r.ok) {
      status("Erro ao salvar fala: " + (dados.error || r.status), !!transcriber);
      return;
    }
    if (dados.aviso) status(dados.aviso, !!transcriber);
    await carregar();
  }

  async function token() {
    const r = await fetch("/api/azure/speech-token");
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.missing ? "Azure não configurado: " + dados.missing.join(", ") : (dados.error || "token"));
    return dados;
  }

  async function liberarMicrofone() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw { name: "SecurityError" };
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((track) => track.stop());
  }

  async function iniciarMicrofone() {
    if (!window.SpeechSDK) throw new Error("SDK do Azure Speech não carregou (sem internet?). Use o campo de texto.");
    try {
      await liberarMicrofone();
    } catch (erro) {
      throw new Error(explicarDispositivo(erro, "microfone"));
    }
    const cred = await token();
    const config = SpeechSDK.SpeechConfig.fromAuthorizationToken(cred.token, cred.region);
    config.speechRecognitionLanguage = "pt-BR";
    const audio = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
    transcriber = new SpeechSDK.ConversationTranscriber(config, audio);
    transcriber.transcribing = (_, e) => {
      el("parcial").textContent = e.result.text ? rotulo(e.result.speakerId) + ": " + e.result.text + "…" : "";
    };
    transcriber.transcribed = (_, e) => {
      el("parcial").textContent = "";
      if (e.result.reason !== SpeechSDK.ResultReason.RecognizedSpeech || !e.result.text) return;
      enviarFala({ texto: e.result.text, locutor: e.result.speakerId || "", offset_ms: Math.round(e.result.offset / 10000) });
    };
    transcriber.canceled = (_, e) => {
      status("Transcrição interrompida: " + (e.errorDetails || e.reason), false);
      parar();
    };
    await new Promise((ok, falha) => transcriber.startTranscribingAsync(ok, falha));
    renovarToken = setInterval(async () => {
      try { transcriber.authorizationToken = (await token()).token; } catch (_) { /* tenta de novo */ }
    }, 9 * 60 * 1000);
  }

  async function iniciar() {
    el("btn-iniciar").disabled = true;
    status("Ligando microfone e câmera…", false);
    let microfone = null;
    try {
      await iniciarMicrofone();
    } catch (erro) {
      transcriber = null;
      microfone = erro.message || String(erro);
    }
    let cameraErro = null;
    if (window.cameraFacial) {
      try { await window.cameraFacial.ligar(); } catch (erro) { cameraErro = erro.message || String(erro); }
    }
    if (microfone) {
      el("btn-iniciar").disabled = false;
      status("Microfone: " + microfone + (cameraErro ? " · Câmera: " + cameraErro : ""), false);
      return;
    }
    el("btn-iniciar").classList.add("d-none");
    el("btn-parar").classList.remove("d-none");
    status("Gravando. Fale normalmente: cada frase entra na conversa ao terminar e as vozes são identificadas sozinhas."
      + (cameraErro ? " (Câmera: " + cameraErro + ")" : ""), true);
  }

  function parar() {
    clearInterval(renovarToken);
    const atual = transcriber;
    transcriber = null;
    el("parcial").textContent = "";
    if (el("btn-iniciar")) {
      el("btn-iniciar").disabled = false;
      el("btn-iniciar").classList.remove("d-none");
      el("btn-parar").classList.add("d-none");
    }
    if (window.cameraFacial) window.cameraFacial.desligar();
    if (atual) {
      atual.stopTranscribingAsync(() => { atual.close(); status("Microfone e câmera desligados.", false); }, () => atual.close());
    } else {
      status("Microfone e câmera desligados.", false);
    }
  }

  window.consultaAoVivo = { sessao, api, carregar, explicarDispositivo };

  if (ativa && el("btn-iniciar")) {
    el("btn-iniciar").addEventListener("click", iniciar);
    el("btn-parar").addEventListener("click", parar);
    el("fala-manual").addEventListener("submit", async (event) => {
      event.preventDefault();
      const campo = el("fala-manual-texto");
      if (!campo.value.trim()) return;
      const papel = el("fala-manual-papel").value;
      await enviarFala({ texto: campo.value, locutor: "digitado-" + papel, papel });
      campo.value = "";
    });
    document.getElementById("ir-encerrar")?.addEventListener("click", parar);
  }
  carregar();
})();
