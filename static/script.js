document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.nav-links a');
    const mainViews = document.querySelectorAll('.main-view');

    // 1. Inicializar la vista de "Inicio"
    const inicioLink = document.querySelector('a[data-view="inicio-view"]');
    if (document.getElementById('inicio-view')) {
        document.getElementById('inicio-view').classList.remove('hidden');
    }
    if (inicioLink) {
        inicioLink.parentElement.classList.add('active');
    }

    // 2. Lógica de Navegación (Mostrar/Ocultar Vistas)
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Prevenir el comportamiento por defecto solo para enlaces de vista local
            if (this.dataset.view) {
                e.preventDefault();
                const viewId = this.dataset.view;

                // Actualizar clases de enlace activo
                navLinks.forEach(l => l.parentElement.classList.remove('active'));
                this.parentElement.classList.add('active');

                // Mostrar la vista seleccionada y ocultar el resto
                mainViews.forEach(view => {
                    view.classList.toggle('hidden', view.id !== viewId);
                });
            }
        });
    });

       // Lógica para el botón "Descargar"
    document.querySelectorAll('.download-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const gameId = this.dataset.gameId;
            fetch(`/download_game/${gameId}`)
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) {
                        // Opcional: actualizar la interfaz de usuario sin recargar
                        location.reload(); 
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Hubo un error al intentar descargar el juego.');
                });
        });
    });
  // Lógica para comentarios
    document.querySelectorAll('.comment-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const gameId = this.querySelector('input[name="game_id"]').value;
            const content = this.querySelector('textarea[name="content"]').value;
            
            fetch('/add_comment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ game_id: gameId, content: content }),
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    this.querySelector('textarea[name="content"]').value = ''; // Limpia el textarea
                    loadComments(gameId); // Vuelve a cargar los comentarios para ver el nuevo
                } else {
                    alert('Error al agregar comentario: ' + data.message);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });


    // 5. Función para cargar y mostrar comentarios
    function loadComments(gameId) {
        const commentsSection = document.querySelector(`.comments-section[data-game-id="${gameId}"] .comments-list`);
        if (!commentsSection) return;

        fetch(`/get_comments/${gameId}`)
            .then(response => response.json())
            .then(comments => {
                commentsSection.innerHTML = ''; // Limpiar lista existente
                
                if (comments && comments.length > 0) {
                    comments.forEach(comment => {
                        const commentElement = document.createElement('div');
                        commentElement.className = 'comment-item';
                        // Nota: Asegúrate que 'created_at' y 'username' se envían desde Flask
                        commentElement.innerHTML = `
                            <strong>${comment.username}</strong>
                            <p>${comment.content}</p>
                            <small>${comment.created_at}</small>
                        `;
                        commentsSection.appendChild(commentElement);
                    });
                } else {
                    commentsSection.innerHTML = '<p>No hay comentarios aún.</p>';
                }
            })
            .catch(error => console.error('Error al cargar comentarios:', error));
    }

    // 6. Cargar comentarios iniciales para todos los juegos
    document.querySelectorAll('.games-list .game-item').forEach(gameItem => {
        const commentForm = gameItem.querySelector('.comment-form');
        if (commentForm) { // Asegúrate de que haya una sección de comentarios
            const gameId = commentForm.querySelector('input[name="game_id"]').value;
            loadComments(gameId);
        }
    });
});