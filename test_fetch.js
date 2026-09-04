fetch('http://127.0.0.1:8000/cases/FAKE')
  .then(async res => {
    console.log('OK:', res.ok, 'Status:', res.status, 'StatusText:', res.statusText);
    const text = await res.text();
    console.log('Body:', text);
  })
  .catch(err => console.error('Fetch err:', err));
