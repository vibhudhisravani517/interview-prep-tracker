document.addEventListener('DOMContentLoaded', function () {

  document.querySelectorAll('.toggle-checkbox').forEach(function (checkbox) {
    checkbox.addEventListener('change', function () {
      var topicId = this.dataset.topicId;
      var card = document.getElementById('topic-card-' + topicId);
      fetch('/toggle/' + topicId, { method: 'POST' })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.completed) { card && card.classList.add('done'); }
          else { card && card.classList.remove('done'); }
        })
        .catch(function () { checkbox.checked = !checkbox.checked; });
    });
  });

  document.querySelectorAll('.status-select').forEach(function (sel) {
    sel.addEventListener('change', function () {
      var taskId = this.dataset.taskId;
      var newStatus = this.value;
      var card = this.closest('.task-card');
      fetch('/tasks/status/' + taskId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (!card) return;
          card.classList.remove('pending', 'in_progress', 'completed');
          card.classList.add(data.status);
          var dot = card.querySelector('.task-status-dot');
          if (dot) {
            dot.className = 'task-status-dot status-' + data.status;
          }
          if (data.status === 'completed') { card.classList.add('completed'); }
          else { card.classList.remove('completed'); }
        });
    });
  });

  // ── Notes ──────────────────────────────────────────────────────────────────

  window.toggleNotePanel = function (topicId, btn) {
    var panel = document.getElementById('note-panel-' + topicId);
    var allBtns = document.querySelectorAll('.note-toggle-btn');
    if (!panel) return;
    var isOpen = panel.style.display !== 'none';
    if (isOpen) {
      panel.style.display = 'none';
      allBtns.forEach(function (b) {
        if (b.dataset.topicId == topicId) b.classList.remove('active');
      });
    } else {
      panel.style.display = 'block';
      allBtns.forEach(function (b) {
        if (b.dataset.topicId == topicId) b.classList.add('active');
      });
      var ta = document.getElementById('note-ta-' + topicId);
      if (ta) { ta.focus(); }
    }
  };

  window.saveNote = function (topicId, btnEl) {
    var ta = document.getElementById('note-ta-' + topicId);
    var msgEl = document.getElementById('saved-msg-' + topicId);
    if (!ta) return;
    var content = ta.value;
    if (btnEl) btnEl.disabled = true;
    fetch('/notes/save/' + topicId, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content })
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (btnEl) btnEl.disabled = false;
        if (msgEl) {
          msgEl.textContent = '✓ Saved at ' + data.updated_at;
          setTimeout(function () { msgEl.textContent = ''; }, 3000);
        }
        var card = document.getElementById('topic-card-' + topicId);
        if (card) {
          var existing = card.querySelector('.badge-note');
          if (!existing && content.trim()) {
            var meta = card.querySelector('.topic-meta');
            if (meta) {
              var badge = document.createElement('span');
              badge.className = 'badge badge-note';
              badge.textContent = '📝 Note saved';
              meta.appendChild(badge);
            }
          } else if (existing && !content.trim()) {
            existing.remove();
          }
        }
      })
      .catch(function () {
        if (btnEl) btnEl.disabled = false;
      });
  };

  window.openNoteEdit = function (topicId, noteId, btn) {
    var panel = document.getElementById('note-edit-' + topicId);
    if (panel) {
      panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      var ta = document.getElementById('note-ta-' + topicId);
      if (ta && panel.style.display !== 'none') ta.focus();
    }
  };

  window.closeNoteEdit = function (topicId) {
    var panel = document.getElementById('note-edit-' + topicId);
    if (panel) panel.style.display = 'none';
  };

  document.querySelectorAll('.flash-close').forEach(function (btn) {
    btn.addEventListener('click', function () { this.parentElement.remove(); });
  });

  setTimeout(function () {
    document.querySelectorAll('.flash').forEach(function (el) { el.remove(); });
  }, 5000);

  document.querySelectorAll('.delete-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm('Are you sure you want to delete this?')) e.preventDefault();
    });
  });
});
