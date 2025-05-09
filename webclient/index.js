import { sha512 } from 'https://esm.sh/@noble/hashes/sha512';
import { etc, sign } from "https://esm.sh/@noble/ed25519";
import { DFS3_USERS, toBytes, base64ToBuffer, bufferToBase64, unlockPrivateKey } from './common.js';

// Error: etc.sha512Sync not set
etc.sha512Sync = sha512;


// ---
// mock api para pruebas
// ---
/*
const originalFetch = window.fetch;

window.fetch = async (url, options) => {
  if (url.endsWith('/auth/challenge')) {
    console.log('[MOCK] POST /api/v1/auth/challenge', options.body);
    return new Response(JSON.stringify({ challenge: 'challenge' }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (url.endsWith('/auth/verify')) {
    console.log('[MOCK] POST /api/v1/auth/verify', options.body);
    return new Response(JSON.stringify({ access_token: "access_token" }), { 
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  }

  // Resto de fetchs sin cambios
  return originalFetch(url, options);
};
*/


// ---
// main
// ---
$(function () {
  const users = JSON.parse(localStorage.getItem(DFS3_USERS) || '{}');
  if (Object.keys(users).length === 0) {
    window.location.href = 'register.html';
    return;
  }

  const $form = $('#login-form');
  const $select = $('#user-select');
  const $error = $('#error-msg');
  const $output = $('#output');

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
    $error.text('');
    $output.text('');

    const userId = $select.val();
    const password = $('#password').val();

    try {
      // Intentamos obtener y desbloquear la clave privada
      const privateKey = await unlockPrivateKey(userId, password);
      $output.text('Clave descifrada correctamente.');

      // Guardamos user_id y private_key en sesión, TODO: buscar forma mas segura
      sessionStorage.setItem('active_user_id', userId);
      sessionStorage.setItem('dfs3_private_key', bufferToBase64(privateKey));

      // Iniciamos el desafio / respuesta enviando nuestro user_id 
      const challengeRes = await fetch('/api/v1/auth/challenge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });

      // TODO: Control de error ???
      // ...

      // Capturamos la respuesta y la firmamos con nuestra clave privada
      const { challenge } = await challengeRes.json();
      const signature = await sign(toBytes(challenge), privateKey);
      const verifyRes = await fetch('/api/v1/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, signature: bufferToBase64(signature) })
      });

      if (verifyRes.ok) {
        // Nos quedamos con el token devuelto 
        const { access_token } = await verifyRes.json();
        sessionStorage.setItem('access_token', access_token);
        console.log('Access token:', access_token);

        // Vamos a la siguiente pagina
        window.location.href = 'upload.html'; 

      } else {
        $error.text('Autenticación fallida.');
      }

    } catch (e) {
      $error.text('Contraseña incorrecta o datos corruptos.');
      console.log(e);
    }

  });

  $('#go-register').on('click', () => {
    window.location.href = 'register.html';
  });

});
