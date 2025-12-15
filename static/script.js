function vote(reviewId, voteType) {
    fetch(`/vote/${reviewId}/${voteType}`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        // If the server indicates unauthorized, show a login prompt.
        if (response.status === 401) {
            alert('Please log in to vote.');
            throw new Error('Unauthorized');
        }
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            // Non-JSON response indicates an error; show a general message
            alert('Unexpected server response.');
            throw new Error('Not JSON response');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            const likes = data.likes || 0;
            const dislikes = data.dislikes || 0;
            const userVote = data.user_vote || 0;

            // Update counts in the UI
            const likesEl = document.getElementById(`likes-${reviewId}`);
            const dislikesEl = document.getElementById(`dislikes-${reviewId}`);
            if (likesEl) likesEl.textContent = likes;
            if (dislikesEl) dislikesEl.textContent = dislikes;

            // Update button appearance based on user vote
            const likeBtn = document.getElementById(`like-btn-${reviewId}`);
            const dislikeBtn = document.getElementById(`dislike-btn-${reviewId}`);
            if (userVote === 1) {
                if (likeBtn) {
                    likeBtn.classList.remove('btn-outline-success');
                    likeBtn.classList.add('btn-success');
                }
                if (dislikeBtn) {
                    dislikeBtn.classList.remove('btn-danger');
                    dislikeBtn.classList.add('btn-outline-danger');
                }
            } else if (userVote === -1) {
                if (dislikeBtn) {
                    dislikeBtn.classList.remove('btn-outline-danger');
                    dislikeBtn.classList.add('btn-danger');
                }
                if (likeBtn) {
                    likeBtn.classList.remove('btn-success');
                    likeBtn.classList.add('btn-outline-success');
                }
            } else {
                // No vote: outline both
                if (likeBtn) {
                    likeBtn.classList.remove('btn-success');
                    likeBtn.classList.add('btn-outline-success');
                }
                if (dislikeBtn) {
                    dislikeBtn.classList.remove('btn-danger');
                    dislikeBtn.classList.add('btn-outline-danger');
                }

        Array.from(tagsSelect.querySelectorAll('optgroup')).forEach(og => {
            const type = og.getAttribute('data-type');
            const disable = (type === 'positive' && !showPositive) || (type === 'negative' && !showNegative);
            Array.from(og.querySelectorAll('option')).forEach(opt => {
                opt.disabled = disable;
                // visually hide options when disabled for better UX
                opt.style.display = disable ? 'none' : '';
            });
        });
    }

    ratingSelect.addEventListener('change', updateTagOptions);
    // initialize on load
    updateTagOptions();
});