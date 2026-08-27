// =========================================================================
// CONFIGURAÇÃO DA API E ESTADOS LOCAIS
// =========================================================================

const API = {
  produtos: '/produtos',
  movimentacoes: '/movimentacoes',
  setores: '/setores',
  relatorios: '/relatorios'
};

let produtosList = [];
let setoresList = [];

// =========================================================================
// INICIALIZAÇÃO DO SISTEMA E EVENTOS GERAIS
// =========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Inicializa os ícones da interface
  if (window.lucide) {
    lucide.createIcons();
  }

  // Controle de Tema (Claro/Escuro)
  initTheme();

  // -----------------------------------------------------------------------
  // EXCLUSÃO DE PRODUTOS E SETORES (Atualização Instantânea)
  // -----------------------------------------------------------------------
  document.addEventListener('click', (event) => {
    // Excluir Produto
    const btnProduto = event.target.closest('.btn-deletar-produto');
    if (btnProduto) {
      const id = btnProduto.dataset.id;
      if (id) deletarProduto(id, btnProduto);
      return;
    }

    // Excluir Setor
    const btnSetor = event.target.closest('.btn-deletar-setor');
    if (btnSetor) {
      const id = btnSetor.dataset.id;
      if (id) deletarSetor(id, btnSetor);
    }
  });

  // -----------------------------------------------------------------------
  // FORMULÁRIOS DE EDIÇÃO (Atualização Silenciosa)
  // -----------------------------------------------------------------------
  const formEditarProduto = document.getElementById('form-editar-produto');
  if (formEditarProduto) {
    formEditarProduto.addEventListener('submit', async (event) => {
      event.preventDefault();
      const id = formEditarProduto.dataset.id;
      if (!id) { alert('ID do produto não encontrado.'); return; }
      await atualizarProduto(event.target, id);
    });
  }

  const formEditarSetor = document.getElementById('form-editar-setor');
  if (formEditarSetor) {
    formEditarSetor.addEventListener('submit', async (event) => {
      event.preventDefault();
      const id = formEditarSetor.dataset.id;
      if (!id) { alert('ID do setor não encontrado.'); return; }
      await atualizarSetor(event.target, id);
    });
  }
});

// Carrega todas as informações ao abrir a tela de Dashboard ou Relatórios
async function loadAllData() {
  await Promise.all([
    fetchProdutos(),
    fetchMovimentacoes(),
    fetchSetores()
  ]);
  if (window.lucide) {
    lucide.createIcons();
  }
}

// =========================================================================
// 1. GESTÃO DE PRODUTOS E ESTOQUE
// =========================================================================

// IMPORTAR PLANILHA DE PRODUTOS
async function importarPlanilha(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('arquivo', file);

  try {
    const res = await fetch('/produtos/importar', {
      method: 'POST',
      body: formData 
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Erro ao importar planilha.');

    alert(data.mensagem || 'Planilha importada com sucesso!');
    await fetchProdutos(); 
  } catch (error) {
    alert('Erro na Importação: ' + error.message);
  } finally {
    event.target.value = '';
    if (window.lucide) lucide.createIcons();
  }
}

// BUSCAR PRODUTOS NA API
async function fetchProdutos() {
  const tbody = document.getElementById('inventory-table-body');
  const criticalContainer = document.getElementById('critical-items-container');
  const selectProdutos = document.getElementById('select-modal-produtos');

  try {
    const res = await fetch(API.produtos);
    if (!res.ok) throw new Error(`Status ${res.status}`);

    produtosList = await res.json();

    // Preenche o Select na tela de Entrada/Saída
    if (selectProdutos) {
      selectProdutos.innerHTML = '<option value="" disabled selected>Selecione o produto...</option>' +
        produtosList.map(produto => {
          const codigo = produto.codigo ? `${produto.codigo} - ` : '';
          return `<option value="${produto.id}">${codigo}${produto.nome}</option>`;
        }).join('');
    }

    renderInventoryTable(produtosList);
    renderCriticalItems(produtosList);

  } catch (error) {
    console.error('Erro ao carregar produtos:', error);
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Erro ao carregar catálogo.</td></tr>`;
    if (criticalContainer) criticalContainer.innerHTML = `<p class="text-muted" style="padding: 1rem 0;">Sem alertas.</p>`;
  }
}

// RENDERIZAR TABELA DE ESTOQUE
function renderInventoryTable(items) {
  const tbody = document.getElementById('inventory-table-body');
  if (!tbody) return;
  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center">Nenhum produto cadastrado.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(produto => {
    const saldo = produto.quantidade_estoque ?? 0;
    const minimo = produto.estoque_minimo ?? 0;
    const unidade = produto.unidade || 'UN';

    let badgeClass = 'badge-success';
    let badgeText = 'Em estoque';

    if (saldo === 0) { badgeClass = 'badge-danger'; badgeText = 'Crítico / Zerado'; }
    else if (saldo <= minimo) { badgeClass = 'badge-warning'; badgeText = 'Estoque baixo'; }

    return `
      <tr>
        <td class="code-col">${produto.codigo || `ID-${produto.id}`}</td>
        <td><strong>${produto.nome}</strong><span class="subtext">${produto.categoria || 'Geral'}</span></td>
        <td>${saldo} ${unidade}</td>
        <td>${minimo}</td>
        <td>${produto.localizacao || 'Almoxarifado'}</td>
        <td><span class="badge ${badgeClass}">● ${badgeText}</span></td>
        <td class="text-right actions-col">
          <button type="button" class="action-btn text-danger btn-deletar-produto" title="Excluir" data-id="${produto.id}">
            <i data-lucide="trash-2"></i>
          </button>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

// RENDERIZAR PAINEL DE ALERTA DE ESTOQUE CRÍTICO
function renderCriticalItems(items) {
  const container = document.getElementById('critical-items-container');
  if (!container) return;

  const criticalItems = items.filter(produto => {
    const quantidade = produto.quantidade_estoque ?? 0;
    const minimo = produto.estoque_minimo ?? 0;
    return quantidade <= minimo;
  });

  if (criticalItems.length === 0) {
    container.innerHTML = `<p class="text-muted" style="padding: 1rem 0;">Todos os materiais estão acima do mínimo.</p>`;
    return;
  }

  container.innerHTML = criticalItems.map(produto => {
    const quantidade = produto.quantidade_estoque ?? 0;
    const minimo = produto.estoque_minimo ?? 0;
    const unidade = produto.unidade || 'UN';
    const isZero = quantidade === 0;

    return `
      <div class="critical-item-row">
        <div class="item-details">
          <h4>${produto.nome}</h4>
          <p>${produto.codigo || `ID-${produto.id}`} · mínimo ${minimo} ${unidade}</p>
        </div>
        <div class="item-stats">
          <span class="stock-count">${quantidade} ${unidade}</span>
          <span class="badge ${isZero ? 'badge-danger' : 'badge-warning'}">● ${isZero ? 'Crítico' : 'Estoque baixo'}</span>
        </div>
      </div>
    `;
  }).join('');
}

// CADASTRAR NOVO PRODUTO (Instantâneo / Otimista)
async function salvarNovoProduto(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  
  const payload = {
    nome: formData.get('nome'),
    categoria: formData.get('categoria') || null,
    descricao: formData.get('descricao') || null,
    estoque_minimo: parseInt(formData.get('estoque_minimo')) || 0
  };

  form.reset(); // Limpa a tela instantaneamente

  // Cria linha fantasma indicando carregamento
  const tbody = document.getElementById('inventory-table-body');
  const tempId = "temp-" + Date.now();
  if (tbody && tbody.innerHTML.includes('Nenhum produto')) tbody.innerHTML = '';
  if (tbody) {
    const tr = document.createElement('tr');
    tr.id = tempId;
    tr.style.opacity = "0.5";
    tr.innerHTML = `
      <td class="code-col">Gerando...</td>
      <td><strong>${payload.nome}</strong><span class="subtext">${payload.categoria || 'Geral'}</span></td>
      <td>0 UN</td>
      <td>${payload.estoque_minimo}</td>
      <td>Almoxarifado</td>
      <td><span class="badge badge-warning">Salvando...</span></td>
      <td></td>
    `;
    tbody.prepend(tr);
  }

  try {
    const res = await fetch('/produtos/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Erro ao cadastrar produto.');
    fetchProdutos(); // Atualiza a tabela com o ID real sem piscar a tela

  } catch (error) { 
    alert('Erro: ' + error.message); 
    if (document.getElementById(tempId)) document.getElementById(tempId).remove();
  }
}

// ATUALIZAR PRODUTO (Silencioso)
async function atualizarProduto(form, produtoId) {
  const formData = new FormData(form);
  const payload = {
    nome: formData.get('nome'),
    categoria: formData.get('categoria') || null,
    descricao: formData.get('descricao') || null,
    estoque_minimo: parseInt(formData.get('estoque_minimo')) || 0
  };

  try {
    const res = await fetch(`/produtos/${produtoId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Erro ao atualizar produto.');
    
    // Fecha modal (se houver algum aberto no CSS) e recarrega a tabela
    const modal = document.querySelector('.modal.show'); 
    if(modal) modal.classList.remove('show');
    fetchProdutos();

  } catch (error) { alert('Erro: ' + error.message); }
}

// EXCLUIR PRODUTO (Instantâneo)
async function deletarProduto(produtoId, btnElement) {
  if (!confirm(`Deseja realmente remover o produto #${produtoId}?`)) return;

  const linha = btnElement.closest('tr');
  if (linha) linha.remove(); // Remove na tela antes de ir no servidor

  try {
    const res = await fetch(`/produtos/${produtoId}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Erro ao excluir produto.');
    }
    fetchProdutos(); // Sincroniza em segundo plano
  } catch (error) { 
    alert('Erro: ' + error.message); 
    fetchProdutos(); // Se der erro, desfaz a exclusão visual
  }
}

// Handler genérico do form HTML de produto
async function handleProdutoSubmit(event) { return salvarNovoProduto(event); }

// FILTRO DE BUSCA (Barra de Pesquisa)
function filterInventoryTable() {
  const input = document.getElementById('inventory-search');
  if (!input) return;

  const query = input.value.toLowerCase().trim();
  const produtosFiltrados = produtosList.filter(produto => {
    const texto = `${produto.codigo || ''} ${produto.nome || ''} ${produto.categoria || ''} ${produto.descricao || ''} ${produto.localizacao || ''}`.toLowerCase();
    return texto.includes(query);
  });
  renderInventoryTable(produtosFiltrados);
}


// =========================================================================
// 2. GESTÃO DE MOVIMENTAÇÕES E SAÍDAS
// =========================================================================

// BUSCAR HISTÓRICO DE MOVIMENTAÇÕES
async function fetchMovimentacoes() {
  const tbody = document.getElementById('transactions-table-body');
  if (!tbody) return;

  try {
    const res = await fetch(API.movimentacoes);
    if (!res.ok) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Histórico indisponível.</td></tr>`;
      return;
    }

    const movimentacoes = await res.json();
    if (!movimentacoes.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">Nenhuma movimentação registrada.</td></tr>`;
      return;
    }

    tbody.innerHTML = movimentacoes.map(movimentacao => {
      const isEntrada = (movimentacao.tipo || '').toUpperCase().includes('ENTRADA');
      const badge = isEntrada ? 'badge-success' : 'badge-warning';
      const dataStr = movimentacao.data_movimentacao ? new Date(movimentacao.data_movimentacao).toLocaleDateString('pt-BR') : '—';

      return `
        <tr>
          <td>${dataStr}</td>
          <td><span class="badge ${badge}">${movimentacao.tipo}</span></td>
          <td>${movimentacao.produto?.nome || movimentacao.produto_id || '—'}</td>
          <td>${movimentacao.quantidade}</td>
          <td>${movimentacao.setor?.nome || '—'}</td>
          <td>${movimentacao.responsavel || '—'}</td>
          <td>${movimentacao.observacao || '—'}</td>
        </tr>
      `;
    }).join('');
  } catch (error) {
    console.error('Erro ao carregar movimentações:', error);
    tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">Histórico indisponível.</td></tr>`;
  }
}

// ENVIAR ENTRADA/SAÍDA SIMPLES
async function enviarMovimentacao(event, tipo) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);

  const produtoId = parseInt(formData.get('produto_id'), 10);
  const quantidade = parseInt(formData.get('quantidade'), 10);
  const setorIdRaw = formData.get('setor_id');
  const observacao = formData.get('observacao');
  const nfe = formData.get('nfe');

  const payload = { tipo: tipo.toLowerCase(), produto_id: produtoId, quantidade: quantidade };

  if (observacao && observacao.trim() !== '') payload.observacao = observacao.trim();
  if (nfe && nfe.trim() !== '') payload.nfe = nfe.trim();
  if (setorIdRaw && setorIdRaw.trim() !== '' && !isNaN(parseInt(setorIdRaw, 10))) payload.setor_id = parseInt(setorIdRaw, 10);

  try {
    const response = await fetch('/movimentacoes/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    if (!response.ok) {
      if (data.detail && Array.isArray(data.detail)) {
        const erros = data.detail.map(e => `Campo [${e.loc.slice(1).join('.')}]: ${e.msg}`).join('\n');
        throw new Error(erros);
      }
      throw new Error(data.detail || 'Erro na validação do formulário.');
    }

    alert('Movimentação registrada com sucesso!');
    if (tipo.toLowerCase() === 'saida' && data.id) {
      window.location.href = `/movimentacoes/html/recibo/${data.id}`;
    } else {
      window.location.href = '/produtos/html/lista';
    }
  } catch (error) { alert('Erro de Validação:\n' + error.message); }
}

// SAÍDA DE MÚLTIPLOS ITENS COM RECIBO
function adicionarLinhaItem() {
  const container = document.getElementById('linhas-produtos-container');
  const templateOptions = document.getElementById('select-produtos-template').innerHTML;

  const tr = document.createElement('tr');
  tr.className = 'item-linha';
  tr.innerHTML = `
    <td>
      <select name="produto_id[]" class="form-control select-produto" required>${templateOptions}</select>
    </td>
    <td>
      <input type="number" name="quantidade[]" class="form-control input-qtd" min="1" value="1" required />
    </td>
    <td style="text-align: center;">
      <button type="button" class="action-btn text-danger" onclick="removerLinhaItem(this)" title="Remover item">
        <i data-lucide="trash-2"></i>
      </button>
    </td>
  `;
  container.appendChild(tr);
  if (window.lucide) lucide.createIcons();
}

function removerLinhaItem(btn) {
  const linhas = document.querySelectorAll('.item-linha');
  if (linhas.length <= 1) { alert('A requisição deve conter pelo menos um item.'); return; }
  btn.closest('tr').remove();
}

async function enviarSaidaMultipla(event) {
  event.preventDefault();
  const setorSelect = document.getElementById('setor_id');
  const setorId = setorSelect.value;
  const setorNome = setorSelect.options[setorSelect.selectedIndex]?.text || 'Geral';
  const nfe = document.getElementById('nfe').value;
  const observacao = document.getElementById('observacao').value;

  const linhas = document.querySelectorAll('.item-linha');
  const itens = [];
  const itensParaRecibo = [];

  linhas.forEach(linha => {
    const select = linha.querySelector('.select-produto');
    const produtoId = select.value;
    const produtoNome = select.options[select.selectedIndex]?.text.split('(')[0].trim() || 'Item';
    const quantidade = linha.querySelector('.input-qtd').value;

    if (produtoId && quantidade) {
      itens.push({ produto_id: parseInt(produtoId, 10), quantidade: parseInt(quantidade, 10) });
      itensParaRecibo.push({ nome: produtoNome, quantidade: parseInt(quantidade, 10) });
    }
  });

  if (itens.length === 0) { alert('Adicione pelo menos um produto para a saída.'); return; }

  const btnSubmit = document.getElementById('btn-submit-saida');
  btnSubmit.disabled = true;
  btnSubmit.innerHTML = 'Processando saída...';

  const agora = new Date();
  const dataHoraISO = agora.toISOString();
  const dataHoraFormatada = agora.toLocaleDateString('pt-BR') + ' às ' + agora.toLocaleTimeString('pt-BR');

  let ultimoIdMovimentacao = null;

  try {
    for (const item of itens) {
      const payload = {
        tipo: 'saida',
        produto_id: item.produto_id,
        quantidade: item.quantidade,
        setor_id: parseInt(setorId, 10),
        nfe: nfe ? nfe.trim() : null,
        observacao: observacao ? observacao.trim() : null,
        data_movimentacao: dataHoraISO
      };

      const response = await fetch('/movimentacoes/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Erro ao registrar item da saída.');
      ultimoIdMovimentacao = data.id;
    }

    sessionStorage.setItem('ultimo_recibo_saida', JSON.stringify({
      setorNome: setorNome,
      nfe: nfe ? nfe.trim() : 'Sem Protocolo',
      responsavel: observacao ? observacao.trim() : 'Servidor Autorizado',
      dataHoraFormatada: dataHoraFormatada,
      itens: itensParaRecibo
    }));

    alert('Saída registrada com sucesso!');
    if (ultimoIdMovimentacao) { window.location.href = `/movimentacoes/html/recibo/${ultimoIdMovimentacao}`; }
    else { window.location.href = '/produtos/html/lista'; }
  } catch (error) {
    alert('Erro ao registrar saída:\n' + error.message);
    btnSubmit.disabled = false;
    btnSubmit.innerHTML = '<i data-lucide="check-circle"></i> Confirmar Saída e Emitir Recibo';
  }
}

// IMPORTAR PLANILHA DE HISTÓRICO ANTIGO DE SAÍDAS
async function importarHistoricoSaidas(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('arquivo', file);

  try {
    alert("Iniciando importação... Isso pode levar alguns segundos dependendo do tamanho da planilha.");
    
    const res = await fetch('/movimentacoes/importar-historico', {
      method: 'POST',
      body: formData 
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Erro ao importar histórico.');
    }

    if (data.erros && data.erros.length > 0) {
      console.warn("Erros na importação de histórico:", data.erros);
      alert(data.mensagem + "\n\nAVISO: Alguns itens não foram importados pois não existiam no catálogo. Aperte F12 para ver a lista no console.");
    } else {
      alert(data.mensagem);
    }
    
    window.location.reload(); // Recarrega para desenhar a tabela e gráficos

  } catch (error) {
    alert('Erro na Importação do Histórico: ' + error.message);
  } finally {
    event.target.value = '';
  }
}


// =========================================================================
// 3. GESTÃO DE SETORES
// =========================================================================

async function fetchSetores() {
  const select = document.getElementById('select-modal-setores');
  const tbody = document.getElementById('sectors-table-body');

  try {
    const res = await fetch(API.setores);
    if (!res.ok) throw new Error('Erro ao carregar setores');

    setoresList = await res.json();

    if (select) {
      select.innerHTML = '<option value="" selected>Nenhum / Geral</option>' +
        setoresList.map(setor => `<option value="${setor.id}">${setor.nome}</option>`).join('');
    }

    if (tbody) {
      if (setoresList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center">Nenhum setor cadastrado.</td></tr>`;
      } else {
        tbody.innerHTML = setoresList.map(setor => `
          <tr>
            <td>${setor.id}</td>
            <td><strong>${setor.nome}</strong></td>
            <td>${setor.secretaria || setor.responsavel || '—'}</td>
            <td class="text-right actions-col">
              <button type="button" class="action-btn text-danger btn-deletar-setor" title="Excluir" data-id="${setor.id}">
                <i data-lucide="trash-2"></i>
              </button>
            </td>
          </tr>
        `).join('');
      }
    }
    if (window.lucide) lucide.createIcons();

  } catch (error) { console.warn('Erro ao carregar setores:', error); }
}

// CADASTRAR NOVO SETOR (Instantâneo / Otimista)
async function salvarNovoSetor(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const payload = { 
    nome: formData.get('nome'), 
    secretaria: formData.get('secretaria') || null 
  };

  form.reset(); // Limpa a tela instantaneamente

  const tbody = document.getElementById('sectors-table-body');
  const tempId = "temp-" + Date.now();
  if (tbody && tbody.innerHTML.includes('Nenhum setor')) tbody.innerHTML = '';
  if (tbody) {
    const tr = document.createElement('tr');
    tr.id = tempId;
    tr.style.opacity = "0.5";
    tr.innerHTML = `
      <td>...</td>
      <td><strong>${payload.nome}</strong></td>
      <td>${payload.secretaria || '—'}</td>
      <td class="text-right"><span class="badge badge-warning">Salvando...</span></td>
    `;
    tbody.prepend(tr);
  }

  try {
    const res = await fetch('/setores/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Erro ao cadastrar setor.');
    fetchSetores(); // Atualiza a tabela invisivelmente

  } catch (error) { 
    alert('Erro: ' + error.message); 
    if (document.getElementById(tempId)) document.getElementById(tempId).remove();
  }
}

// ATUALIZAR SETOR (Silencioso)
async function atualizarSetor(form, setorId) {
  const formData = new FormData(form);
  const payload = { 
    nome: formData.get('nome'), 
    secretaria: formData.get('secretaria') || null 
  };

  try {
    const res = await fetch(`/setores/${setorId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Erro ao atualizar setor.');
    fetchSetores(); // Não redireciona, apenas atualiza a tela
  } catch (error) { alert('Erro: ' + error.message); }
}

// EXCLUIR SETOR (Instantâneo)
async function deletarSetor(setorId, btnElement) {
  if (!confirm(`Deseja realmente remover o setor #${setorId}?`)) return;

  const linha = btnElement.closest('tr');
  if (linha) linha.remove(); // Some na tela na hora

  try {
    const res = await fetch(`/setores/${setorId}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Não é possível excluir este setor pois ele possui histórico vinculado.');
    }
    fetchSetores();
  } catch (error) { 
    alert('Erro: ' + error.message); 
    fetchSetores(); // Desfaz a exclusão em caso de erro
  }
}


// =========================================================================
// 4. CONTROLE DE TEMA (DARK/LIGHT MODE)
// =========================================================================

function initTheme() {
  const themeToggleBtn = document.getElementById('theme-toggle');
  let savedTheme = 'dark';

  try { savedTheme = localStorage.getItem('sialm_theme') || 'dark'; } catch (e) {}

  if (savedTheme === 'light') {
    document.documentElement.classList.add('light-theme');
    updateThemeIcon('moon');
  } else {
    document.documentElement.classList.remove('light-theme');
    updateThemeIcon('sun');
  }

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const isLight = document.documentElement.classList.toggle('light-theme');
      const currentTheme = isLight ? 'light' : 'dark';
      try { localStorage.setItem('sialm_theme', currentTheme); } catch (e) {}
      updateThemeIcon(isLight ? 'moon' : 'sun');
    });
  }
}

function updateThemeIcon(iconName) {
  const iconElem = document.getElementById('theme-icon');
  if (iconElem) {
    iconElem.setAttribute('data-lucide', iconName);
    if (window.lucide) lucide.createIcons();
  }
}