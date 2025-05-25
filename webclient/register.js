import { DFS3_USERS, encryptPrivateKey, bufferToBase64, sha256Hex } from './common.js';
import { generateKeys } from './crypto.js';


// ---
// Guarda claves en localStorage
// ---
async function saveUserKeysToStorage(userId, alias, publicKey, privateKey, password) {
  // Ciframos la clave privada
  const { encryptedPrivateKey, salt, iv } = await encryptPrivateKey(privateKey, password);

  // Existen claves previas? añadimos
  const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
  users[userId] = {
    alias: alias, 
    public_key: bufferToBase64(publicKey),
    encrypted_private_key: bufferToBase64(encryptedPrivateKey),
    salt: bufferToBase64(salt),
    iv: bufferToBase64(iv)
  };

  // Y salvamos a storage
  localStorage.setItem(DFS3_USERS, JSON.stringify(users));
}


// ---
// main
// ---

$(function () {
  const $error = $('#error-msg');
  const $status = $('#upload-status');

  // Activación de btn si introducida password
  $('#register-btn').prop('disabled', true);
  $('#alias').on('input', function () {
    $('#register-btn').prop('disabled', $(this).val().trim().length == 0);
  });


  // ---
  // Click register-btn
  // ---
  $('#register-btn').on('click', async () => {
    const alias = $('#alias').val()?.trim();
    const fullname = $('#fullname').val()?.trim();
    const email = $('#email').val()?.trim();
    const pass1 = $('#password1').val();
    const pass2 = $('#password2').val();

    if (pass1 !== pass2) {
      $error.text('Las contraseñas no coinciden.');
      return;
    }

    if (!alias || !pass1) {
      $error.text('Completar los campos obligatorios.');
      return;
    }

    // Para evitar reintentos, reset status
    $('#register-form :input').prop('disabled', true);
    $error.text('');
    $status.show(); // muestra el spinner

    try {
      const { publicKey, privateKey } = await generateKeys(pass1);
      const userId = await sha256Hex(publicKey);

      // Muestra lo que se enviaría al servidor
      const user = {
        user_id: userId,
        alias,
        name: fullname,
        email,
        public_key: bufferToBase64(publicKey)
      };

      const response = await fetch('/api/v1/auth/register', {
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
        body: JSON.stringify(user)
      });

      // Todo ok, guarda la clave privada cifrada en localStorage
      await saveUserKeysToStorage(userId, alias, publicKey, privateKey, pass1);

      if (response.ok) {
        // Redirigimos a pagina principal
        $status.text("Usuario registrado. Redirigiendo...");
        setTimeout(() => window.location.href = 'login.html', 2000);

      } else {
        const e = await response.text();
        throw new Error(e);
      }

    } catch (e) {
      $status.hide();
      $error.text('Error durante el registro.');
      $('#register-form :input').prop('disabled', false);
      console.log(e);
    }

  });

});
