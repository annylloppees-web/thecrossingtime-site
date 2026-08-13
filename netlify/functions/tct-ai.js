// The Crossing Time — proxy seguro para a IA (Anthropic).
// A CHAVE nunca fica no site: vem da variável de ambiente ANTHROPIC_API_KEY,
// definida no painel do Netlify (Site settings → Environment variables).
// O flipbook chama esta função; a função é que fala com a Anthropic.

const MODEL = process.env.AI_MODEL || 'claude-sonnet-4-20250514';
const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages';

exports.handler = async function (event) {
  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
  };
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: cors, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: cors, body: JSON.stringify({ error: 'Method not allowed' }) };

  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) return { statusCode: 500, headers: cors, body: JSON.stringify({ error: 'ANTHROPIC_API_KEY não configurada no Netlify.' }) };

  let payload;
  try { payload = JSON.parse(event.body || '{}'); }
  catch (e) { return { statusCode: 400, headers: cors, body: JSON.stringify({ error: 'JSON inválido.' }) }; }

  var mode = payload.mode === 'ask' ? 'ask' : 'summary';
  var lang = ['pt', 'fr', 'en'].indexOf(payload.lang) >= 0 ? payload.lang : 'pt';
  var image = (payload.image || '').replace(/^data:image\/[a-z]+;base64,/, '');
  var question = (payload.question || '').toString().slice(0, 1000);
  var pageNum = payload.page || '';

  if (!image) return { statusCode: 400, headers: cors, body: JSON.stringify({ error: 'Falta a imagem da página.' }) };

  var LANGNAME = { pt: 'Português', fr: 'Français', en: 'English' };
  var instruction;
  if (mode === 'ask') {
    if (!question) return { statusCode: 400, headers: cors, body: JSON.stringify({ error: 'Falta a pergunta.' }) };
    instruction = 'Você é um assistente da revista "The Crossing Time — Porta-Voz do Imigrante". '
      + 'Olhe esta página (imagem) e responda à pergunta do leitor com base APENAS no que está na página. '
      + 'Se a resposta não estiver na página, diga-o com franqueza. Responda em ' + LANGNAME[lang]
      + ', de forma clara e breve.\n\nPergunta do leitor: ' + question;
  } else {
    instruction = 'Analise esta página da revista "The Crossing Time — Porta-Voz do Imigrante" e faça um '
      + 'resumo aprofundado (5 a 8 frases) em ' + LANGNAME[lang]
      + ': quem é a pessoa/assunto, a história, os factos e a mensagem principal. Seja fiel à página, sem inventar.';
  }

  var body = {
    model: MODEL,
    max_tokens: 700,
    messages: [{
      role: 'user',
      content: [
        { type: 'image', source: { type: 'base64', media_type: 'image/jpeg', data: image } },
        { type: 'text', text: instruction }
      ]
    }]
  };

  try {
    var r = await fetch(ANTHROPIC_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify(body)
    });
    var data = await r.json();
    if (!r.ok) {
      return { statusCode: r.status, headers: cors, body: JSON.stringify({ error: (data && data.error && data.error.message) || 'Erro na API.' }) };
    }
    var text = (data.content && data.content[0] && data.content[0].text) ? data.content[0].text : '';
    return { statusCode: 200, headers: cors, body: JSON.stringify({ text: text }) };
  } catch (e) {
    return { statusCode: 502, headers: cors, body: JSON.stringify({ error: 'Falha ao contactar a IA.' }) };
  }
};
