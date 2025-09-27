document.addEventListener("DOMContentLoaded", () => {
  // ----- EDIT PROFILE MODAL -----
  const editBtn = document.querySelector(".edit-btn");
  const editModal = document.getElementById("editModal");
  const closeEdit = document.querySelector(".close-btn");
  const cancelEdit = document.querySelector(".cancel-btn");

  // Open edit modal
  editBtn.addEventListener("click", () => {
    editModal.style.display = "flex";
  });

  // Close edit modal with X
  closeEdit.addEventListener("click", () => {
    editModal.style.display = "none";
  });

  // Close edit modal with Cancel
  cancelEdit.addEventListener("click", () => {
    editModal.style.display = "none";
  });

  // ----- DELETE PROFILE MODAL -----
  const deleteBtn = document.querySelector(".delete-btn"); // outer button
  const deleteModal = document.getElementById("deleteModal");
  const closeDelete = document.querySelector(".close-delete");
  const cancelDelete = document.querySelector(".cancel-delete");

  // Open delete modal
  deleteBtn.addEventListener("click", () => {
    deleteModal.style.display = "flex";
  });

  // Close delete modal with X
  closeDelete.addEventListener("click", () => {
    deleteModal.style.display = "none";
  });

  // Close delete modal with Cancel
  cancelDelete.addEventListener("click", () => {
    deleteModal.style.display = "none";
  });

  // Close modals if clicking outside
  window.addEventListener("click", (e) => {
    if (e.target === editModal) editModal.style.display = "none";
    if (e.target === deleteModal) deleteModal.style.display = "none";
  });
});
