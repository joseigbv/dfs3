$(function () {
  const backendUrl = localStorage.getItem("backend_url");
  if (backendUrl) {
    // Si ya existe, seleccionamos ese valor en el desplegable
    $('#backend-select').val(backendUrl);
  }

  $('#connect-btn').on('click', () => {
    const selected = $('#backend-select').val();
    if (!selected) {
      alert("Selecciona un nodo para continuar");
      return;
    }

    localStorage.setItem("backend_url", selected);
    window.location.href = "login.html";
  });
});
