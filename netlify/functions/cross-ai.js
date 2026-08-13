/*  CROSS AI — funcao do lado do servidor
 *  Formato CommonJS (handler v1): o mais compativel com deploys manuais.
 *
 *  A chave da API NUNCA aparece no site. Fica na variavel de ambiente
 *  ANTHROPIC_API_KEY, definida no painel da Netlify:
 *  Project configuration > Environment variables
 */

var LIMITE_POR_HORA = 30;
var visitas = {};

function travao(ip) {
  var agora = Date.now();
  var h = agora - 3600000;
  var lista = (visitas[ip] || []).filter(function (t) { return t > h; });
  if (lista.length >= LIMITE_POR_HORA) return false;
  lista.push(agora);
  visitas[ip] = lista;
  if (Object.keys(visitas).length > 3000) visitas = {};
  return true;
}

function json(codigo, dados) {
  return {
    statusCode: codigo,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(dados)
  };
}

exports.handler = async function (event) {
  if (event.httpMethod === 'GET') {
    return json(200, { estado: 'viva', chave: !!process.env.ANTHROPIC_API_KEY });
  }
  if (event.httpMethod !== 'POST') {
    return json(405, { erro: 'metodo' });
  }

  var chave = process.env.ANTHROPIC_API_KEY;
  if (!chave) {
    return json(503, { erro: 'nao_configurado',
      texto: 'A CROSS AI ainda nao esta configurada neste site.' });
  }

  var cab = event.headers || {};
  var ip = cab['x-nf-client-connection-ip'] || cab['client-ip'] || 'desconhecido';
  if (!travao(ip)) {
    return json(429, { erro: 'limite',
      texto: 'Muitas perguntas seguidas. Tente daqui a pouco.' });
  }

  var corpo;
  try {
    corpo = JSON.parse(event.body || '{}');
  } catch (e) {
    return json(400, { erro: 'pedido_invalido' });
  }

  if (!corpo.system || !Array.isArray(corpo.messages) || !corpo.messages.length) {
    return json(400, { erro: 'pedido_invalido' });
  }
  if ((event.body || '').length > 220000) {
    return json(413, { erro: 'pedido_grande' });
  }

  try {
    var r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': chave,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 1000,
        system: corpo.system,
        messages: corpo.messages.slice(-6)
      })
    });

    if (!r.ok) {
      var detalhe = await r.text();
      console.error('Anthropic ' + r.status + ': ' + detalhe.slice(0, 500));
      return json(502, { erro: 'api', estado: r.status });
    }

    var dados = await r.json();
    var texto = (dados.content || [])
      .filter(function (b) { return b.type === 'text'; })
      .map(function (b) { return b.text; })
      .join('\n')
      .trim();

    return json(200, { texto: texto });
  } catch (e) {
    console.error('CROSS AI: ' + (e && e.message));
    return json(502, { erro: 'rede' });
  }
};
