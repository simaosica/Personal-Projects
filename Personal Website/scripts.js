function showSection(sectionId) {
    // Hide all sections
    const sections = document.querySelectorAll('.main-content section');
    sections.forEach(section => section.classList.add('hidden'));

    // Show the selected section
    const selectedSection = document.getElementById(sectionId);
    if (selectedSection) {
        selectedSection.classList.remove('hidden');
    }
}
