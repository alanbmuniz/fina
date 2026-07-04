import { useState, useEffect, useRef } from "react";

// ─── Palette & Theme ────────────────────────────────────────────────────────
// Deep navy + emerald + amber — premium fintech feel

const DB_KEY = "finapp_data_v1";

function loadDB() {
  try {
    const raw = localStorage.getItem(DB_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveDB(data) {
  try { localStorage.setItem(DB_KEY, JSON.stringify(data)); } catch {}
}

function initialDB() {
  return {
    user: { name: "Usuário", monthlyIncome: 0 },
    transactions: [],
    goals: [],
    cards: [
      { id: 1, name: "Nubank", limit: 5000, used: 1240, color: "#8b5cf6" },
      { id: 2, name: "Itaú Visa", limit: 8000, used: 3100, color: "#f59e0b" },
    ],
    messages: [],
  };
}

// ─── Utility ────────────────────────────────────────────────────────────────
function fmt(n) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n);
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

// ─── Claude API call ────────────────────────────────────────────────────────
async function askClaude(userMessage, db) {
  const summary = buildFinancialSummary(db);
  const systemPrompt = `Você é a FINA, assistente financeira pessoal inteligente e empática. 
Fale sempre em português brasileiro, de forma conversacional, amigável e direta — como uma consultora financeira de confiança.
Seja objetiva: dê orientações práticas, não discursos longos.
Use emojis com moderação para deixar a conversa mais humanizada.

DADOS FINANCEIROS DO USUÁRIO:
${summary}

Regras:
- Ao analisar compras, considere saúde financeira real (saldo, cartões, metas)
- Alerte sobre riscos de endividamento quando necessário
- Projete cenários futuros quando perguntado
- Se o usuário quiser adicionar receita/despesa, oriente-o a usar o painel lateral
- Nunca invente dados; use apenas os fornecidos
- Respostas em até 4 parágrafos curtos`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1000,
      system: systemPrompt,
      messages: [{ role: "user", content: userMessage }],
    }),
  });
  const data = await response.json();
  return data.content?.map(b => b.text || "").join("") || "Desculpe, não consegui processar sua mensagem.";
}

function buildFinancialSummary(db) {
  const now = new Date();
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const txs = db.transactions || [];
  const monthTxs = txs.filter(t => t.date?.startsWith(thisMonth));
  const income = monthTxs.filter(t => t.type === "income").reduce((s, t) => s + t.amount, 0);
  const expenses = monthTxs.filter(t => t.type === "expense").reduce((s, t) => s + t.amount, 0);
  const balance = income - expenses;
  const totalCardDebt = (db.cards || []).reduce((s, c) => s + c.used, 0);
  const totalCardLimit = (db.cards || []).reduce((s, c) => s + c.limit, 0);
  const goals = (db.goals || []).map(g => `${g.name}: R$${g.saved} de R$${g.target}`).join(", ") || "nenhuma meta cadastrada";
  const cards = (db.cards || []).map(c => `${c.name}: R$${c.used} usados de R$${c.limit}`).join(", ");

  return `
Renda mensal declarada: R$${db.user?.monthlyIncome || 0}
Receitas este mês: R$${income.toFixed(2)}
Despesas este mês: R$${expenses.toFixed(2)}
Saldo do mês: R$${balance.toFixed(2)}
Cartões de crédito: ${cards}
Total usado nos cartões: R$${totalCardDebt} de R$${totalCardLimit} disponíveis
Metas financeiras: ${goals}
Últimas transações: ${txs.slice(-5).map(t => `${t.description} (${t.type === "income" ? "+" : "-"}R$${t.amount})`).join(", ") || "nenhuma"}
  `.trim();
}

// ─── Components ─────────────────────────────────────────────────────────────

function Avatar({ name }) {
  const initials = name?.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase() || "U";
  return (
    <div style={{
      width: 38, height: 38, borderRadius: "50%",
      background: "linear-gradient(135deg, #10b981, #059669)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 14, fontWeight: 700, color: "#fff", flexShrink: 0,
    }}>{initials}</div>
  );
}

function FinaAvatar() {
  return (
    <div style={{
      width: 38, height: 38, borderRadius: "50%",
      background: "linear-gradient(135deg, #0ea5e9, #6366f1)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 18, flexShrink: 0,
    }}>💎</div>
  );
}

function Bubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div style={{
      display: "flex", gap: 10, alignItems: "flex-start",
      flexDirection: isUser ? "row-reverse" : "row",
      marginBottom: 16,
    }}>
      {isUser ? <Avatar name="Eu" /> : <FinaAvatar />}
      <div style={{
        maxWidth: "72%",
        background: isUser
          ? "linear-gradient(135deg, #10b981 0%, #059669 100%)"
          : "rgba(255,255,255,0.06)",
        border: isUser ? "none" : "1px solid rgba(255,255,255,0.1)",
        color: "#f0fdf4",
        borderRadius: isUser ? "18px 4px 18px 18px" : "4px 18px 18px 18px",
        padding: "12px 16px",
        fontSize: 14,
        lineHeight: 1.6,
        backdropFilter: "blur(8px)",
        whiteSpace: "pre-wrap",
      }}>
        {msg.content}
        <div style={{ fontSize: 11, opacity: 0.5, marginTop: 4, textAlign: isUser ? "right" : "left" }}>
          {msg.time}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub, color, icon }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.05)",
      border: `1px solid ${color}33`,
      borderRadius: 16,
      padding: "16px 20px",
      flex: 1, minWidth: 140,
    }}>
      <div style={{ fontSize: 22, marginBottom: 4 }}>{icon}</div>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color, marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function CardWidget({ card }) {
  const pct = Math.min((card.used / card.limit) * 100, 100);
  const color = pct > 80 ? "#ef4444" : pct > 50 ? "#f59e0b" : "#10b981";
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 12, padding: "12px 16px", marginBottom: 10,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{card.name}</span>
        <span style={{ fontSize: 12, color }}>{pct.toFixed(0)}%</span>
      </div>
      <div style={{ background: "rgba(255,255,255,0.1)", borderRadius: 999, height: 6 }}>
        <div style={{ width: `${pct}%`, background: color, borderRadius: 999, height: "100%", transition: "width 0.6s" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 12, color: "#94a3b8" }}>
        <span>Usado: {fmt(card.used)}</span>
        <span>Limite: {fmt(card.limit)}</span>
      </div>
    </div>
  );
}

function GoalWidget({ goal, onUpdate }) {
  const pct = Math.min((goal.saved / goal.target) * 100, 100);
  const remaining = goal.target - goal.saved;
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(16,185,129,0.2)",
      borderRadius: 12, padding: "12px 16px", marginBottom: 10,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>🎯 {goal.name}</span>
        <span style={{ fontSize: 12, color: "#10b981" }}>{pct.toFixed(0)}%</span>
      </div>
      <div style={{ background: "rgba(255,255,255,0.1)", borderRadius: 999, height: 6 }}>
        <div style={{ width: `${pct}%`, background: "linear-gradient(90deg,#10b981,#6366f1)", borderRadius: 999, height: "100%", transition: "width 0.6s" }} />
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 6 }}>
        {fmt(goal.saved)} / {fmt(goal.target)} — faltam {fmt(remaining)}
      </div>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────────────
export default function App() {
  const [db, setDb] = useState(() => loadDB() || initialDB());
  const [tab, setTab] = useState("chat"); // chat | dashboard | add | goals
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ type: "expense", description: "", amount: "", date: today(), category: "Outros" });
  const [goalForm, setGoalForm] = useState({ name: "", target: "", saved: "" });
  const [notification, setNotification] = useState("");
  const chatRef = useRef(null);

  useEffect(() => { saveDB(db); }, [db]);
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [db.messages, loading]);

  function notify(msg) {
    setNotification(msg);
    setTimeout(() => setNotification(""), 3000);
  }

  const now = new Date();
  const thisMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const txs = db.transactions || [];
  const monthTxs = txs.filter(t => t.date?.startsWith(thisMonth));
  const totalIncome = monthTxs.filter(t => t.type === "income").reduce((s, t) => s + t.amount, 0);
  const totalExpense = monthTxs.filter(t => t.type === "expense").reduce((s, t) => s + t.amount, 0);
  const balance = totalIncome - totalExpense;
  const totalCardDebt = (db.cards || []).reduce((s, c) => s + c.used, 0);

  async function sendMessage() {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input.trim(), time: new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) };
    const newMsgs = [...(db.messages || []), userMsg];
    setDb(d => ({ ...d, messages: newMsgs }));
    setInput("");
    setLoading(true);
    try {
      const reply = await askClaude(userMsg.content, { ...db, messages: newMsgs });
      const aiMsg = { role: "assistant", content: reply, time: new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) };
      setDb(d => ({ ...d, messages: [...d.messages, aiMsg] }));
    } catch (e) {
      setDb(d => ({ ...d, messages: [...d.messages, { role: "assistant", content: "⚠️ Erro ao conectar com a IA. Tente novamente.", time: "" }] }));
    }
    setLoading(false);
  }

  function addTransaction() {
    if (!form.description || !form.amount) { notify("Preencha todos os campos!"); return; }
    const tx = { id: Date.now(), ...form, amount: parseFloat(form.amount) };
    setDb(d => ({ ...d, transactions: [...(d.transactions || []), tx] }));
    setForm({ type: "expense", description: "", amount: "", date: today(), category: "Outros" });
    notify(form.type === "income" ? "✅ Receita adicionada!" : "✅ Despesa adicionada!");
  }

  function addGoal() {
    if (!goalForm.name || !goalForm.target) { notify("Preencha nome e valor alvo!"); return; }
    const g = { id: Date.now(), name: goalForm.name, target: parseFloat(goalForm.target), saved: parseFloat(goalForm.saved || 0) };
    setDb(d => ({ ...d, goals: [...(d.goals || []), g] }));
    setGoalForm({ name: "", target: "", saved: "" });
    notify("🎯 Meta criada!");
  }

  const cats = ["Alimentação", "Moradia", "Transporte", "Saúde", "Lazer", "Educação", "Vestuário", "Outros"];

  const styles = {
    app: {
      minHeight: "100vh",
      background: "linear-gradient(160deg, #020617 0%, #0f172a 50%, #020c1b 100%)",
      color: "#e2e8f0",
      fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
      display: "flex", flexDirection: "column",
    },
    header: {
      background: "rgba(255,255,255,0.03)",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      padding: "14px 20px",
      display: "flex", alignItems: "center", justifyContent: "space-between",
    },
    logo: {
      display: "flex", alignItems: "center", gap: 10,
      fontSize: 20, fontWeight: 800,
      background: "linear-gradient(90deg, #10b981, #6366f1)",
      WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
    },
    nav: {
      display: "flex", gap: 4, padding: "10px 16px",
      background: "rgba(255,255,255,0.02)",
      borderBottom: "1px solid rgba(255,255,255,0.06)",
      overflowX: "auto",
    },
    navBtn: (active) => ({
      padding: "8px 16px", borderRadius: 20, border: "none", cursor: "pointer",
      fontSize: 13, fontWeight: 600, whiteSpace: "nowrap",
      background: active ? "linear-gradient(135deg,#10b981,#6366f1)" : "transparent",
      color: active ? "#fff" : "#94a3b8",
      transition: "all 0.2s",
    }),
    content: { flex: 1, overflowY: "auto", padding: "0" },
    chatArea: { display: "flex", flexDirection: "column", height: "calc(100vh - 130px)" },
    messages: { flex: 1, overflowY: "auto", padding: "20px 16px" },
    inputRow: {
      display: "flex", gap: 8, padding: "12px 16px",
      background: "rgba(255,255,255,0.03)",
      borderTop: "1px solid rgba(255,255,255,0.08)",
    },
    textInput: {
      flex: 1, background: "rgba(255,255,255,0.08)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 24, padding: "10px 18px",
      color: "#f1f5f9", fontSize: 14, outline: "none",
    },
    sendBtn: {
      background: "linear-gradient(135deg,#10b981,#6366f1)",
      border: "none", borderRadius: 24,
      padding: "10px 20px", color: "#fff",
      fontWeight: 700, cursor: "pointer", fontSize: 14,
    },
    section: { padding: "20px 16px" },
    label: { fontSize: 12, color: "#94a3b8", marginBottom: 4, display: "block", textTransform: "uppercase", letterSpacing: 0.8 },
    fieldInput: {
      width: "100%", background: "rgba(255,255,255,0.07)",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 10, padding: "10px 14px",
      color: "#f1f5f9", fontSize: 14, outline: "none",
      boxSizing: "border-box", marginBottom: 14,
    },
    fieldSelect: {
      width: "100%", background: "#1e293b",
      border: "1px solid rgba(255,255,255,0.12)",
      borderRadius: 10, padding: "10px 14px",
      color: "#f1f5f9", fontSize: 14, outline: "none",
      boxSizing: "border-box", marginBottom: 14,
    },
    btn: (color) => ({
      width: "100%", padding: "12px", borderRadius: 12,
      border: "none", cursor: "pointer", fontWeight: 700,
      fontSize: 15, color: "#fff",
      background: color || "linear-gradient(135deg,#10b981,#6366f1)",
    }),
    typeRow: { display: "flex", gap: 8, marginBottom: 14 },
    typeBtn: (active, color) => ({
      flex: 1, padding: "10px", borderRadius: 10,
      border: `2px solid ${active ? color : "rgba(255,255,255,0.1)"}`,
      background: active ? `${color}22` : "transparent",
      color: active ? color : "#64748b",
      cursor: "pointer", fontWeight: 600, fontSize: 14,
    }),
    metricsRow: { display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 },
    sectionTitle: { fontSize: 13, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, marginBottom: 10, fontWeight: 700 },
    txItem: {
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.05)",
      fontSize: 14,
    },
    notif: {
      position: "fixed", bottom: 80, left: "50%", transform: "translateX(-50%)",
      background: "#10b981", color: "#fff", padding: "10px 24px",
      borderRadius: 24, fontWeight: 600, fontSize: 14, zIndex: 100,
      boxShadow: "0 4px 20px rgba(16,185,129,0.4)",
      transition: "opacity 0.3s",
    },
  };

  const welcomeMsgs = db.messages?.length === 0 ? [{
    role: "assistant",
    content: `Olá! 👋 Eu sou a **FINA**, sua assistente financeira inteligente.\n\nPosso te ajudar a:\n• 📊 Analisar sua saúde financeira\n• 💳 Monitorar seus cartões de crédito\n• 🎯 Planejar seus objetivos\n• 💡 Orientar sobre compras\n• 📈 Fazer projeções financeiras\n\nComo posso te ajudar hoje?`,
    time: "",
  }] : db.messages;

  return (
    <div style={styles.app}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.logo}>💎 FINA</div>
        <div style={{ fontSize: 12, color: "#64748b" }}>Assistente Financeiro IA</div>
      </div>

      {/* Nav */}
      <div style={styles.nav}>
        {[
          { id: "chat", label: "💬 Chat" },
          { id: "dashboard", label: "📊 Dashboard" },
          { id: "add", label: "➕ Lançamentos" },
          { id: "goals", label: "🎯 Metas" },
        ].map(t => (
          <button key={t.id} style={styles.navBtn(tab === t.id)} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Chat */}
      {tab === "chat" && (
        <div style={styles.chatArea}>
          <div style={styles.messages} ref={chatRef}>
            {welcomeMsgs.map((m, i) => <Bubble key={i} msg={m} />)}
            {loading && (
              <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 16 }}>
                <FinaAvatar />
                <div style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "4px 18px 18px 18px", padding: "12px 16px" }}>
                  <span style={{ animation: "pulse 1s infinite", opacity: 0.6 }}>FINA está digitando...</span>
                </div>
              </div>
            )}
          </div>
          <div style={styles.inputRow}>
            <input
              style={styles.textInput}
              placeholder="Pergunte algo à FINA..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendMessage()}
            />
            <button style={styles.sendBtn} onClick={sendMessage} disabled={loading}>
              {loading ? "..." : "Enviar"}
            </button>
          </div>
        </div>
      )}

      {/* Dashboard */}
      {tab === "dashboard" && (
        <div style={styles.section}>
          <div style={styles.metricsRow}>
            <MetricCard label="Receitas" value={fmt(totalIncome)} icon="💚" color="#10b981" sub="este mês" />
            <MetricCard label="Despesas" value={fmt(totalExpense)} icon="🔴" color="#ef4444" sub="este mês" />
          </div>
          <div style={styles.metricsRow}>
            <MetricCard label="Saldo" value={fmt(balance)} icon={balance >= 0 ? "✅" : "⚠️"} color={balance >= 0 ? "#10b981" : "#ef4444"} />
            <MetricCard label="Dívida Cartões" value={fmt(totalCardDebt)} icon="💳" color="#f59e0b" />
          </div>

          <div style={{ ...styles.sectionTitle, marginTop: 10 }}>Cartões de Crédito</div>
          {(db.cards || []).map(c => <CardWidget key={c.id} card={c} />)}

          <div style={styles.sectionTitle}>Últimas Transações</div>
          {txs.slice(-8).reverse().map(t => (
            <div key={t.id} style={styles.txItem}>
              <div>
                <div style={{ fontWeight: 500 }}>{t.description}</div>
                <div style={{ fontSize: 12, color: "#64748b" }}>{t.category} · {t.date}</div>
              </div>
              <div style={{ fontWeight: 700, color: t.type === "income" ? "#10b981" : "#ef4444" }}>
                {t.type === "income" ? "+" : "-"}{fmt(t.amount)}
              </div>
            </div>
          ))}
          {txs.length === 0 && <div style={{ color: "#64748b", fontSize: 14 }}>Nenhuma transação ainda.</div>}
        </div>
      )}

      {/* Add Transaction */}
      {tab === "add" && (
        <div style={styles.section}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>Novo Lançamento</div>
          <div style={styles.typeRow}>
            <button style={styles.typeBtn(form.type === "income", "#10b981")} onClick={() => setForm(f => ({ ...f, type: "income" }))}>
              ↑ Receita
            </button>
            <button style={styles.typeBtn(form.type === "expense", "#ef4444")} onClick={() => setForm(f => ({ ...f, type: "expense" }))}>
              ↓ Despesa
            </button>
          </div>
          <label style={styles.label}>Descrição</label>
          <input style={styles.fieldInput} placeholder="Ex: Salário, Mercado..." value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <label style={styles.label}>Valor (R$)</label>
          <input style={styles.fieldInput} type="number" placeholder="0,00" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
          <label style={styles.label}>Data</label>
          <input style={styles.fieldInput} type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
          <label style={styles.label}>Categoria</label>
          <select style={styles.fieldSelect} value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
            {cats.map(c => <option key={c}>{c}</option>)}
          </select>
          <button style={styles.btn(form.type === "income" ? "linear-gradient(135deg,#10b981,#059669)" : "linear-gradient(135deg,#ef4444,#dc2626)")} onClick={addTransaction}>
            {form.type === "income" ? "➕ Adicionar Receita" : "➕ Adicionar Despesa"}
          </button>

          <div style={{ ...styles.sectionTitle, marginTop: 28 }}>Histórico</div>
          {txs.slice(-10).reverse().map(t => (
            <div key={t.id} style={styles.txItem}>
              <div>
                <div style={{ fontWeight: 500 }}>{t.description}</div>
                <div style={{ fontSize: 12, color: "#64748b" }}>{t.category} · {t.date}</div>
              </div>
              <div style={{ fontWeight: 700, color: t.type === "income" ? "#10b981" : "#ef4444" }}>
                {t.type === "income" ? "+" : "-"}{fmt(t.amount)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Goals */}
      {tab === "goals" && (
        <div style={styles.section}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>Minhas Metas</div>
          {(db.goals || []).map(g => <GoalWidget key={g.id} goal={g} />)}
          {(db.goals || []).length === 0 && <div style={{ color: "#64748b", fontSize: 14, marginBottom: 20 }}>Nenhuma meta cadastrada ainda.</div>}

          <div style={{ ...styles.sectionTitle, marginTop: 16 }}>Nova Meta</div>
          <label style={styles.label}>Nome do Objetivo</label>
          <input style={styles.fieldInput} placeholder="Ex: Viagem para Europa, iPhone..." value={goalForm.name} onChange={e => setGoalForm(f => ({ ...f, name: e.target.value }))} />
          <label style={styles.label}>Valor Alvo (R$)</label>
          <input style={styles.fieldInput} type="number" placeholder="5000" value={goalForm.target} onChange={e => setGoalForm(f => ({ ...f, target: e.target.value }))} />
          <label style={styles.label}>Já guardei (R$)</label>
          <input style={styles.fieldInput} type="number" placeholder="0" value={goalForm.saved} onChange={e => setGoalForm(f => ({ ...f, saved: e.target.value }))} />
          <button style={styles.btn()} onClick={addGoal}>🎯 Criar Meta</button>
        </div>
      )}

      {/* Notification */}
      {notification && <div style={styles.notif}>{notification}</div>}
    </div>
  );
}
