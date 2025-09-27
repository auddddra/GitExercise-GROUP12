document.addEventListener("DOMContentLoaded", () => {
  const editBtn = document.querySelector(".edit-btn");
  const modal = document.getElementById("editModal");
  const closeBtn = document.querySelector(".close-btn");
  const cancelBtn = document.querySelector(".cancel-btn");

  // Open modal
  editBtn.addEventListener("click", () => {
    modal.style.display = "flex";
  });

  // Close modal with X
  closeBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // Close modal with Cancel
  cancelBtn.addEventListener("click", () => {
    modal.style.display = "none";
  });

  // Close modal if clicking outside
  window.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.style.display = "none";
    }
  });
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

// Close if clicking outside
window.addEventListener("click", (e) => {
  if (e.target === deleteModal) {
    deleteModal.style.display = "none";
  }
});