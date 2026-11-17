/* Internação: publicar anomalias, exames de vídeo e áudio, e replay do monitor.
   Cada bloco só roda se a tela tiver os elementos dele. */
(() => {
  const el = (id) => document.getElementById(id);
  const paciente = () => (el("patient_id") ? el("patient_id").value : "");
  const lista = (itens) => (itens && itens.length ? itens.map((i) => "• " + i).join("\n") : "Nenhum alerta novo.");

  if (el("publish")) {
    el("publish").addEventListener("click", async () => {
      el("publish-out").textContent = "Publicando…";
      const r = await fetch("/api/fase4/anomalias/alertas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: paciente() }),
      });
      const body = await r.json();
      el("publish-out").textContent = r.ok
        ? "Nível " + (body.level === "high" ? "alto" : "baixo") + ".\n" + lista(body.new_alerts)
        : "Não foi possível publicar: " + (body.error || r.status);
    });
  }

  if (el("analyze")) {
    let stream = null;
    let gravado = null;
    const saida = el("video-out");
    const mostrar = (body) => {
      const rel = body.report || {};
      const linhas = [rel.summary || "Sem resumo."];
      (rel.deviations || []).forEach((d) => linhas.push("Postura: " + (d.detail || JSON.stringify(d))));
      (rel.zone_events || []).forEach((z) => linhas.push("Área crítica: " + (z.detail || JSON.stringify(z))));
      if (body.warning) linhas.push("", "Aviso: " + body.warning);
      linhas.push("", lista(body.new_alerts));
      saida.textContent = linhas.join("\n");
    };
    const enviar = async (blob, nome) => {
      saida.textContent = "Analisando o vídeo…";
      const dados = new FormData();
      dados.append("patient_id", paciente());
      dados.append("file", blob, nome);
      const r = await fetch("/api/fase4/video/arquivo", { method: "POST", body: dados });
      mostrar(await r.json());
    };
    el("cam-start").addEventListener("click", async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      } catch (erro) {
        saida.textContent = "Câmera indisponível: " + (erro.message || erro);
        return;
      }
      el("preview").srcObject = stream;
      await el("preview").play();
      el("cam-rec").disabled = false;
    });
    el("cam-rec").addEventListener("click", async () => {
      if (!stream) return;
      el("cam-rec").disabled = true;
      const partes = [];
      const gravador = new MediaRecorder(stream, { mimeType: "video/webm" });
      gravador.ondataavailable = (e) => { if (e.data.size) partes.push(e.data); };
      const fim = new Promise((ok) => { gravador.onstop = ok; });
      gravador.start();
      saida.textContent = "Gravando 5 segundos…";
      await new Promise((ok) => setTimeout(ok, 5000));
      gravador.stop();
      await fim;
      gravado = new Blob(partes, { type: "video/webm" });
      el("cam-rec").disabled = false;
      saida.textContent = "Gravação pronta. Clique em Analisar vídeo.";
    });
    el("analyze").addEventListener("click", async () => {
      const arquivo = el("file").files[0];
      if (arquivo) return enviar(arquivo, arquivo.name);
      if (gravado) return enviar(gravado, "webcam.webm");
      saida.textContent = "Escolha um arquivo ou grave 5 segundos com a webcam.";
    });
  }

  if (el("audio-form")) {
    const preencher = (body, estado) => {
      el("a-status").textContent = estado;
      const rel = body.report || {};
      const voz = rel.vocal || body.vocal || {};
      el("a-text").textContent = rel.transcript || "—";
      el("a-sent").textContent = rel.sentiment || "—";
      el("a-crit").textContent = (rel.critical_terms || []).join(", ") || "—";
      el("a-voc").textContent = (voz.fatigue ? "fadiga" : "sem fadiga") + " · "
        + (voz.respiratory_effort ? "esforço respiratório" : "sem esforço respiratório");
      el("a-alerts").textContent = (body.new_alerts || []).join(" · ") || "nenhum novo";
    };
    const enviar = async (dados) => {
      el("a-status").textContent = "Processando…";
      const r = await fetch("/api/fase4/audio", { method: "POST", body: dados });
      const body = await r.json();
      if (body.error === "azure_nao_configurado") {
        return preencher(body, "Azure não configurada (faltam " + (body.missing || []).join(", ") + "). Traços vocais abaixo.");
      }
      preencher(body, r.ok ? "Concluído" : "Erro: " + (body.error || r.status));
    };
    el("audio-form").addEventListener("submit", (e) => {
      e.preventDefault();
      if (!el("audio-file").files[0]) {
        el("a-status").textContent = "Escolha um WAV ou use a amostra.";
        return;
      }
      const dados = new FormData();
      dados.append("patient_id", paciente());
      dados.append("file", el("audio-file").files[0]);
      enviar(dados);
    });
    el("sample").addEventListener("click", () => {
      const dados = new FormData();
      dados.append("patient_id", paciente());
      dados.append("use_sample", "1");
      enviar(dados);
    });
  }

  if (el("replay")) {
    const SINAIS = {
      hr: { faixa: [45, 120], escala: [30, 180] },
      spo2: { faixa: [92, 100], escala: [80, 100] },
      sbp: { faixa: [90, 180], escala: [60, 220] },
      dbp: { faixa: [50, 110], escala: [30, 130] },
    };
    const JANELA = 24;
    const ESTADOS = { normal: ["Normal", "pill-sucesso"], fora_da_faixa: ["Fora da faixa", "pill-perigo"], fora_do_padrao: ["Fora do padrão", "pill-aviso"] };
    let historico = {};
    let pausado = false;
    const cor = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
    const dormir = (ms) => new Promise((ok) => setTimeout(ok, ms));

    const desenhar = (sinal) => {
      const tela = el("g-" + sinal);
      const dpr = window.devicePixelRatio || 1;
      const largura = tela.clientWidth, altura = tela.clientHeight;
      tela.width = largura * dpr; tela.height = altura * dpr;
      const ctx = tela.getContext("2d");
      ctx.scale(dpr, dpr);
      const [min, max] = SINAIS[sinal].escala;
      const y = (v) => altura - ((Math.min(max, Math.max(min, v)) - min) / (max - min)) * altura;
      const [fmin, fmax] = SINAIS[sinal].faixa;
      ctx.fillStyle = cor("--sucesso-suave");
      ctx.fillRect(0, y(fmax), largura, y(fmin) - y(fmax));
      const pontos = historico[sinal] || [];
      if (!pontos.length) return;
      const x = (i) => (i / (JANELA - 1)) * (largura - 8) + 4;
      ctx.strokeStyle = cor("--primaria"); ctx.lineWidth = 2; ctx.beginPath();
      pontos.forEach((p, i) => (i ? ctx.lineTo(x(i), y(p.v)) : ctx.moveTo(x(i), y(p.v))));
      ctx.stroke();
      pontos.forEach((p, i) => {
        ctx.fillStyle = p.estado === "fora_da_faixa" ? cor("--perigo") : p.estado === "fora_do_padrao" ? cor("--aviso") : cor("--primaria");
        ctx.beginPath(); ctx.arc(x(i), y(p.v), p.estado === "normal" ? 2.5 : 4, 0, Math.PI * 2); ctx.fill();
      });
    };

    const registrar = (hora, texto, classe) => {
      const log = el("monitor-log");
      if (log.querySelector(".lista-vazia")) log.replaceChildren();
      const item = document.createElement("li");
      item.className = "alerta-item" + (classe === "pill-aviso" ? " ciente" : "");
      const corpo = document.createElement("div");
      const titulo = document.createElement("div");
      titulo.className = "lista-principal";
      titulo.textContent = hora;
      const detalhe = document.createElement("div");
      detalhe.className = "lista-sec";
      detalhe.textContent = texto;
      corpo.append(titulo, detalhe);
      item.appendChild(corpo);
      log.prepend(item);
    };

    const mostrar = (vital, avaliacao) => {
      const estado = avaliacao ? avaliacao.estado : "normal";
      for (const sinal of Object.keys(SINAIS)) {
        if (vital[sinal] === undefined || vital[sinal] === null) continue;
        (historico[sinal] ||= []).push({ v: vital[sinal], estado });
        historico[sinal] = historico[sinal].slice(-JANELA);
        el("v-" + sinal).textContent = Math.round(vital[sinal]);
        const [fmin, fmax] = SINAIS[sinal].faixa;
        el("v-" + sinal).closest(".sinal").classList.toggle("fora", vital[sinal] < fmin || vital[sinal] > fmax);
        desenhar(sinal);
      }
      const [rotulo, classe] = ESTADOS[estado];
      el("estado-atual").textContent = rotulo;
      el("estado-atual").className = "pill " + classe;
      el("motivos-atual").textContent = avaliacao && avaliacao.motivos.length ? avaliacao.motivos.join(" · ") : "Medição dentro do esperado.";
      if (estado !== "normal") registrar(vital.recorded_at.slice(11, 16), rotulo + ": " + avaliacao.motivos.join(" · "), classe);
    };

    el("pausar-monitor").addEventListener("click", () => {
      pausado = !pausado;
      el("pausar-monitor").textContent = pausado ? "Continuar" : "Pausar";
    });

    el("replay").addEventListener("click", async () => {
      el("replay").disabled = true;
      el("pausar-monitor").disabled = false;
      historico = {};
      el("monitor-log").replaceChildren();
      registrar("", "Leitura iniciada.", "");
      Object.keys(SINAIS).forEach(desenhar);
      el("monitor-progresso").textContent = "Carregando o registro…";
      try {
        const serie = await fetch("/api/fase4/monitor/serie?patient_id=" + encodeURIComponent(paciente())).then((r) => r.json());
        await fetch("/api/fase4/monitor/reset", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ patient_id: paciente() }),
        });
        const porHora = {};
        for (const v of serie.vitals || []) (porHora[v.recorded_at] ||= { t: v.recorded_at }).vital = v;
        for (const m of serie.movement || []) (porHora[m.recorded_at] ||= { t: m.recorded_at }).movement = m;
        const eventos = Object.values(porHora).sort((a, b) => a.t.localeCompare(b.t));
        if (!eventos.length) {
          el("monitor-progresso").textContent = "Sem registro para este paciente. Rode python -m infrastructure.persistencia.seed.";
          return;
        }
        let alertas = 0;
        for (let i = 0; i < eventos.length; i += 1) {
          while (pausado) await dormir(200);
          const r = await fetch("/api/fase4/monitor/tick", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ patient_id: paciente(), vital: eventos[i].vital || null, movement: eventos[i].movement || null }),
          });
          const body = await r.json();
          if (eventos[i].vital) mostrar(eventos[i].vital, body.avaliacao);
          for (const alerta of body.new_alerts || []) {
            alertas += 1;
            registrar(eventos[i].t.slice(11, 16), "Alerta enviado à equipe: " + alerta, "pill-perigo");
          }
          el("monitor-progresso").textContent = "Medição " + (i + 1) + " de " + eventos.length + " · " + alertas + " alerta(s)";
          await dormir(1000 / Number(el("velocidade").value || 1));
        }
        el("monitor-progresso").textContent = "Leitura concluída · " + eventos.length + " medições · " + alertas + " alerta(s)";
      } catch (erro) {
        el("monitor-progresso").textContent = "Leitura interrompida: " + (erro.message || erro);
      } finally {
        el("replay").disabled = false;
        el("pausar-monitor").disabled = true;
        pausado = false;
        el("pausar-monitor").textContent = "Pausar";
      }
    });
    window.addEventListener("resize", () => Object.keys(SINAIS).forEach(desenhar));
    Object.keys(SINAIS).forEach(desenhar);
  }
})();
