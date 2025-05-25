import { sha512 } from 'https://esm.sh/@noble/hashes/sha512';
import { etc, sign } from "https://esm.sh/@noble/ed25519";
import { DFS3_USERS, toBytes, base64ToBuffer, bufferToBase64, unlockPrivateKey } from './common.js';

// Error: etc.sha512Sync not set
etc.sha512Sync = sha512;


// ---
// main
// ---
$(function () {
  const $form = $('#login-form');
  const $select = $('#user-select');
  const $error = $('#error-msg');
  const $status = $('#upload-status');

  // Hay usuarios o registramos?
  const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
  if (Object.keys(users).length === 0) {
    window.location.href = 'register.html';
    return;
  }

  // Llenar el selector de usuarios (alias + user_id)
  for (const [userId, user] of Object.entries(users)) {
    $select.append($('<option>').val(userId).text(`${user.alias} (${userId.slice(0, 18)}...)`));
  }

  // Activación de btn si introducida password
  $('#login-btn').prop('disabled', true);
  $('#password').on('input', function () {
    $('#login-btn').prop('disabled', $(this).val().trim().length == 0);
  });


  // ---
  // click login-btn
  // ---
  $('#login-btn').on('click', async () => {
    const userId = $select.val();
    const password = $('#password').val();

    try {
      // Para evitar reintentos, reset status
      $('#login-form :input').prop('disabled', true);
      $error.text('');
      $status.show(); // muestra el spinner

      // Intentamos obtener y desbloquear la clave privada
      const privateKey = await unlockPrivateKey(userId, password);

      // Guardamos user_id y private_key en sesión, TODO: buscar forma mas segura
      sessionStorage.setItem('active_user_id', userId);
      sessionStorage.setItem('private_key', bufferToBase64(privateKey));

      // Iniciamos el desafio / respuesta enviando nuestro user_id 
      const challengeRes = await fetch('/api/v1/auth/challenge', {
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
        body: JSON.stringify({ user_id: userId })
      });

      // TODO: Control de error ???
      // ...

      // Capturamos la respuesta y la firmamos con nuestra clave privada
      const { challenge } = await challengeRes.json();
      const signature = await sign(toBytes(challenge), privateKey);
      const verifyRes = await fetch('/api/v1/auth/verify', {
        headers: { 'Content-Type': 'application/json' },
        method: 'POST',
        body: JSON.stringify({ user_id: userId, signature: bufferToBase64(signature) })
      });

      if (verifyRes.ok) {
        // Nos quedamos con el token devuelto 
        const { access_token } = await verifyRes.json();
        sessionStorage.setItem('access_token', access_token);

        // Vamos a la pagina principal
        $status.text("Acceso concedido. Redirigiendo...");
        setTimeout(() => window.location.href = 'index.html', 2000);

        // Solo para debug
        console.log(access_token);

      } else {
        const e = await verifyRes.text();
        throw new Error(e);
      }

    } catch (e) {
      $status.hide();
      $error.text('Autenticación fallida.');
      $('#login-form :input').prop('disabled', false);
      console.log(e);
    }

  });


  // ---
  // Click register
  // ---
  $('#go-register').on('click', () => {
    window.location.href = 'register.html';
  });

});
