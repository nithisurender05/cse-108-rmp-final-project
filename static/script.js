function vote(reviewId, voteType) {
    fetch(`/vote/${reviewId}/${voteType}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Vote recorded!');
            // Ideally, you would update the UI count here without reload
        } else {
            alert('Something went wrong.');
        }
    })
    .catch(error => console.error('Error:', error));
}
