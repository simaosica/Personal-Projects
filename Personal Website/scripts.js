document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.buttons');
    const contentSections = document.querySelectorAll('.content-section');

    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const target = this.getAttribute('data-target');

            contentSections.forEach(section => {
                section.style.display = 'none';
            });

            document.getElementById(target).style.display = 'block';
        });
    });

    // Show the home content by default
    document.getElementById('home-content').style.display = 'block';
});